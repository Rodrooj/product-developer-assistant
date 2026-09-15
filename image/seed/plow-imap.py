#!/usr/bin/env python3
"""Small, dependency-free IMAP bridge optimized for agent triage.

The bridge intentionally separates cheap metadata retrieval from message-body
retrieval. Credentials are read only from environment variables and are never
accepted as CLI arguments.
"""
from __future__ import annotations

import argparse
import email
import email.header
import email.policy
import imaplib
import json
import os
import re
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Iterable


class ImapClientError(RuntimeError):
    pass


def die(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        die(f"missing required environment variable: {name}")
    return value


def decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out).strip()


def address_list(value: str | None) -> list[dict[str, str]]:
    result = []
    for name, addr in getaddresses([value or ""]):
        if addr:
            result.append({"name": decode_header(name), "email": addr})
    return result


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, OverflowError):
        return value


def text_part(msg: Message, max_chars: int) -> tuple[str, bool]:
    candidates: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            ctype = part.get_content_type().lower()
            if ctype == "text/plain":
                try:
                    payload = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    if isinstance(payload, bytes):
                        payload = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                candidates.append(str(payload))
            elif ctype == "text/html" and not candidates:
                payload = part.get_payload(decode=True) or b""
                if isinstance(payload, bytes):
                    candidates.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        try:
            payload = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True) or b""
            if isinstance(payload, bytes):
                payload = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        candidates.append(str(payload))
    text = "\n\n".join(x.strip() for x in candidates if x and x.strip())
    truncated = len(text) > max_chars
    return text[:max_chars], truncated


def attachments(msg: Message) -> list[dict[str, object]]:
    result = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        disposition = (part.get("Content-Disposition") or "").lower()
        if filename or "attachment" in disposition:
            payload = part.get_payload(decode=True) or b""
            result.append({
                "filename": decode_header(filename) if filename else None,
                "content_type": part.get_content_type(),
                "size": len(payload),
            })
    return result


def connect() -> imaplib.IMAP4_SSL:
    host = env("PLOW_IMAP_HOST", required=True)
    port = int(env("PLOW_IMAP_PORT", "993"))
    username = env("PLOW_IMAP_USERNAME", required=True)
    password = env("PLOW_IMAP_PASSWORD", required=True)
    context = ssl.create_default_context()
    try:
        client = imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=30)
        client.login(username, password)
        return client
    except Exception as exc:
        raise ImapClientError(f"IMAP connection/login failed: {exc}") from exc


def decode_mailbox(raw: bytes | str) -> str:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    match = re.search(r'\)\s+"[^"]*"\s+(.+)$', text)
    value = match.group(1) if match else text
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace('\\"', '"').replace('\\\\', '\\')


def cmd_mailboxes(client: imaplib.IMAP4_SSL) -> None:
    status, rows = client.list()
    if status != "OK":
        raise ImapClientError("LIST failed")
    for row in rows or []:
        print(json.dumps({"mailbox": decode_mailbox(row)}, ensure_ascii=False))


def select(client: imaplib.IMAP4_SSL, mailbox: str) -> None:
    status, data = client.select(mailbox, readonly=True)
    if status != "OK":
        raise ImapClientError(f"cannot select mailbox: {mailbox}")


def uid_search(client: imaplib.IMAP4_SSL, criteria: list[str]) -> list[int]:
    status, data = client.uid("SEARCH", None, *criteria)
    if status != "OK":
        raise ImapClientError("SEARCH failed")
    raw = data[0] or b""
    return [int(x) for x in raw.split() if x.isdigit()]


def search_since(days: int) -> str:
    date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    return f"SINCE {date}"


def compact_envelope(uid: int, fetch_data: bytes | str) -> dict[str, object]:
    raw = fetch_data if isinstance(fetch_data, bytes) else fetch_data.encode()
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    refs = decode_header(msg.get("References"))
    return {
        "uid": uid,
        "message_id": decode_header(msg.get("Message-ID")),
        "in_reply_to": decode_header(msg.get("In-Reply-To")),
        "references": refs.split() if refs else [],
        "date": parse_date(msg.get("Date")),
        "subject": decode_header(msg.get("Subject")),
        "from": address_list(msg.get("From")),
        "to": address_list(msg.get("To")),
        "cc": address_list(msg.get("Cc")),
        "reply_to": address_list(msg.get("Reply-To")),
        "size": len(raw),
        "has_attachment": any(bool(p.get_filename()) for p in msg.walk()),
    }


def cmd_list(client: imaplib.IMAP4_SSL, args: argparse.Namespace) -> None:
    select(client, args.mailbox)
    criteria = ["ALL"]
    if args.unread:
        criteria = ["UNSEEN"]
    if args.since is not None:
        criteria.append(search_since(args.since))
    uids = uid_search(client, criteria)
    uids = uids[-args.limit:]
    if not uids:
        return
    status, data = client.uid(
        "FETCH", ",".join(map(str, uids)), "(UID FLAGS INTERNALDATE RFC822.SIZE ENVELOPE BODYSTRUCTURE)"
    )
    if status != "OK":
        raise ImapClientError("FETCH metadata failed")
    by_uid: dict[int, dict[str, object]] = {}
    for item in data or []:
        if not isinstance(item, tuple):
            continue
        meta = item[0]
        body = item[1]
        match = re.search(rb"UID\s+(\d+)", meta)
        if not match:
            continue
        uid = int(match.group(1))
        # RFC822 ENVELOPE is not an RFC5322 message, so use a small header fetch
        # for portable parsing. BODYSTRUCTURE remains available as a cheap size
        # and MIME-shape hint from the same server-side operation.
        by_uid[uid] = {"uid": uid, "raw_meta": meta.decode("utf-8", errors="replace")}
    # Portable compact header fetch; one round trip for the selected UID set.
    status, data = client.uid("FETCH", ",".join(map(str, uids)), "(UID BODY.PEEK[HEADER.FIELDS (DATE FROM TO CC REPLY-TO SUBJECT MESSAGE-ID IN-REPLY-TO REFERENCES)])")
    if status != "OK":
        raise ImapClientError("FETCH headers failed")
    for item in data or []:
        if not isinstance(item, tuple):
            continue
        meta, header = item
        match = re.search(rb"UID\s+(\d+)", meta)
        if not match:
            continue
        uid = int(match.group(1))
        row = compact_envelope(uid, header)
        row["mailbox"] = args.mailbox
        row["seen"] = b"\\Seen" in meta
        row["raw_size_hint"] = by_uid.get(uid, {}).get("raw_meta", "")
        print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))


def parse_uid_list(values: Iterable[str]) -> list[int]:
    result = []
    for value in values:
        for token in value.split(","):
            if token.isdigit():
                result.append(int(token))
    return sorted(set(result))


def cmd_fetch(client: imaplib.IMAP4_SSL, args: argparse.Namespace) -> None:
    select(client, args.mailbox)
    uids = parse_uid_list(args.uid)
    if not uids:
        raise ImapClientError("at least one numeric UID is required")
    for uid in uids:
        section = f"BODY.PEEK[]<0.{args.body_limit}>" if args.body_limit else "BODY.PEEK[]"
        status, data = client.uid("FETCH", str(uid), f"(UID {section})")
        if status != "OK":
            raise ImapClientError(f"FETCH failed for UID {uid}")
        payload = None
        for item in data or []:
            if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
                payload = item[1]
                break
        if payload is None:
            continue
        msg = email.message_from_bytes(payload, policy=email.policy.default)
        text, truncated = text_part(msg, args.text_limit)
        result = {
            "mailbox": args.mailbox,
            "uid": uid,
            "message_id": decode_header(msg.get("Message-ID")),
            "date": parse_date(msg.get("Date")),
            "subject": decode_header(msg.get("Subject")),
            "from": address_list(msg.get("From")),
            "to": address_list(msg.get("To")),
            "cc": address_list(msg.get("Cc")),
            "reply_to": address_list(msg.get("Reply-To")),
            "in_reply_to": decode_header(msg.get("In-Reply-To")),
            "references": decode_header(msg.get("References")).split(),
            "body": text,
            "body_truncated": truncated,
            "attachments": attachments(msg),
        }
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def cmd_search(client: imaplib.IMAP4_SSL, args: argparse.Namespace) -> None:
    select(client, args.mailbox)
    # The query is passed as one IMAP search criterion. This keeps the CLI small
    # while allowing standard server-side IMAP search expressions.
    criteria = args.query if isinstance(args.query, list) else [args.query]
    uids = uid_search(client, criteria)
    for uid in uids[-args.limit:]:
        print(json.dumps({"mailbox": args.mailbox, "uid": uid}, separators=(",", ":")))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Minimal IMAP bridge for Plow email triage")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("mailboxes")
    listing = sub.add_parser("list")
    listing.add_argument("--mailbox", default="INBOX")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--unread", action="store_true")
    listing.add_argument("--since", type=int, help="only messages from the last N days")
    fetching = sub.add_parser("fetch")
    fetching.add_argument("--mailbox", default="INBOX")
    fetching.add_argument("--uid", action="append", required=True)
    fetching.add_argument("--body-limit", type=int, default=0, help="max raw bytes fetched per message; 0 means full")
    fetching.add_argument("--text-limit", type=int, default=12000)
    searching = sub.add_parser("search")
    searching.add_argument("--mailbox", default="INBOX")
    searching.add_argument("--query", nargs="+", required=True)
    searching.add_argument("--limit", type=int, default=100)
    return p


def main() -> int:
    args = parser().parse_args()
    client = None
    try:
        client = connect()
        if args.command == "mailboxes":
            cmd_mailboxes(client)
        elif args.command == "list":
            cmd_list(client, args)
        elif args.command == "fetch":
            cmd_fetch(client, args)
        elif args.command == "search":
            cmd_search(client, args)
        return 0
    except ImapClientError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"unexpected error: {exc.__class__.__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 3
    finally:
        if client is not None:
            try:
                client.logout()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
