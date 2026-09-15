#!/usr/bin/env python3
"""Dependency-free IMAP bridge optimized for agent triage.

Credentials are read from PLOW_IMAP_HOST, PLOW_IMAP_PORT, PLOW_IMAP_USERNAME,
and PLOW_IMAP_PASSWORD. They are never accepted as command-line arguments.
"""
from __future__ import annotations
import argparse, email, email.header, email.policy, imaplib, json, os, re, ssl, sys
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime

class ImapClientError(RuntimeError): pass

def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImapClientError(f"missing required environment variable: {name}")
    return value

def decode_header(value):
    if not value: return ""
    out=[]
    for text, charset in email.header.decode_header(value):
        out.append(text.decode(charset or "utf-8", errors="replace") if isinstance(text, bytes) else text)
    return "".join(out).strip()

def address_list(value):
    return [{"name": decode_header(n), "email": a} for n,a in getaddresses([value or ""]) if a]

def parse_date(value):
    if not value: return None
    try: return parsedate_to_datetime(value).isoformat()
    except (TypeError,ValueError,OverflowError): return value

def text_part(msg: Message, max_chars):
    candidates=[]
    parts=msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart() or "attachment" in (part.get("Content-Disposition") or "").lower(): continue
        if part.get_content_type().lower() not in ("text/plain","text/html"): continue
        try: payload=part.get_content()
        except Exception:
            raw=part.get_payload(decode=True) or b""
            payload=raw.decode(part.get_content_charset() or "utf-8", errors="replace") if isinstance(raw,bytes) else raw
        if payload: candidates.append(str(payload).strip())
    text="\n\n".join(x for x in candidates if x)
    return text[:max_chars], len(text)>max_chars

def attachments(msg):
    out=[]
    for part in msg.walk():
        if part.is_multipart(): continue
        filename=part.get_filename(); disp=(part.get("Content-Disposition") or "").lower()
        if filename or "attachment" in disp:
            raw=part.get_payload(decode=True) or b""
            out.append({"filename":decode_header(filename) if filename else None,"content_type":part.get_content_type(),"size":len(raw)})
    return out

def connect():
    context=ssl.create_default_context()
    client=imaplib.IMAP4_SSL(env("PLOW_IMAP_HOST",required=True),int(env("PLOW_IMAP_PORT","993")),ssl_context=context,timeout=30)
    client.login(env("PLOW_IMAP_USERNAME",required=True),env("PLOW_IMAP_PASSWORD",required=True))
    return client

def select(client, mailbox):
    status,_=client.select(mailbox,readonly=True)
    if status!="OK": raise ImapClientError(f"cannot select mailbox: {mailbox}")

def uid_search(client, criteria):
    status,data=client.uid("SEARCH",None,*criteria)
    if status!="OK": raise ImapClientError("SEARCH failed")
    return [int(x) for x in (data[0] or b"").split() if x.isdigit()]

def cmd_mailboxes(client):
    status,rows=client.list()
    if status!="OK": raise ImapClientError("LIST failed")
    for row in rows or []:
        text=row.decode("utf-8",errors="replace") if isinstance(row,bytes) else row
        match=re.search(r'\)\s+"[^"]*"\s+(.+)$',text); value=match.group(1) if match else text
        value=value.strip('"').replace('\\"','"').replace('\\\\','\\')
        print(json.dumps({"mailbox":value},ensure_ascii=False,separators=(",",":")))

def compact_header(uid, raw, mailbox, flags=None):
    msg=email.message_from_bytes(raw,policy=email.policy.default)
    refs=decode_header(msg.get("References"))
    return {"mailbox":mailbox,"uid":uid,"message_id":decode_header(msg.get("Message-ID")),"in_reply_to":decode_header(msg.get("In-Reply-To")),"references":refs.split() if refs else [],"date":parse_date(msg.get("Date")),"subject":decode_header(msg.get("Subject")),"from":address_list(msg.get("From")),"to":address_list(msg.get("To")),"cc":address_list(msg.get("Cc")),"reply_to":address_list(msg.get("Reply-To")),"seen":bool(flags and b"\\Seen" in flags),"has_attachment":False}

def cmd_list(client,args):
    select(client,args.mailbox); criteria=["UNSEEN" if args.unread else "ALL"]
    if args.since is not None: criteria.append(f"SINCE {(datetime.now(timezone.utc)-timedelta(days=args.since)).strftime('%d-%b-%Y')}")
    uids=uid_search(client,criteria)[-args.limit:]
    if not uids:return
    status,data=client.uid("FETCH",",".join(map(str,uids)),"(UID FLAGS BODY.PEEK[HEADER.FIELDS (DATE FROM TO CC REPLY-TO SUBJECT MESSAGE-ID IN-REPLY-TO REFERENCES)])")
    if status!="OK": raise ImapClientError("FETCH headers failed")
    for item in data or []:
        if not isinstance(item,tuple): continue
        meta,header=item; match=re.search(rb"UID\s+(\d+)",meta)
        if match:
            row=compact_header(int(match.group(1)),header,args.mailbox,meta)
            print(json.dumps(row,ensure_ascii=False,separators=(",",":")))

def cmd_fetch(client,args):
    select(client,args.mailbox)
    uids=sorted({int(x) for value in args.uid for x in value.split(",") if x.isdigit()})
    if not uids: raise ImapClientError("at least one numeric UID is required")
    for uid in uids:
        section=f"BODY.PEEK[]<0.{args.body_limit}>" if args.body_limit else "BODY.PEEK[]"
        status,data=client.uid("FETCH",str(uid),f"(UID {section})")
        if status!="OK": raise ImapClientError(f"FETCH failed for UID {uid}")
        payload=next((x[1] for x in data or [] if isinstance(x,tuple) and len(x)>1 and isinstance(x[1],bytes)),None)
        if payload is None: continue
        msg=email.message_from_bytes(payload,policy=email.policy.default); text,truncated=text_part(msg,args.text_limit)
        result={"mailbox":args.mailbox,"uid":uid,"message_id":decode_header(msg.get("Message-ID")),"date":parse_date(msg.get("Date")),"subject":decode_header(msg.get("Subject")),"from":address_list(msg.get("From")),"to":address_list(msg.get("To")),"cc":address_list(msg.get("Cc")),"reply_to":address_list(msg.get("Reply-To")),"in_reply_to":decode_header(msg.get("In-Reply-To")),"references":decode_header(msg.get("References")).split(),"body":text,"body_truncated":truncated,"attachments":attachments(msg)}
        print(json.dumps(result,ensure_ascii=False,separators=(",",":")))

def cmd_search(client,args):
    select(client,args.mailbox); uids=uid_search(client,args.query)
    for uid in uids[-args.limit:]: print(json.dumps({"mailbox":args.mailbox,"uid":uid},separators=(",",":")))

def parser():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("mailboxes")
    x=sub.add_parser("list"); x.add_argument("--mailbox",default="INBOX"); x.add_argument("--limit",type=int,default=100); x.add_argument("--unread",action="store_true"); x.add_argument("--since",type=int)
    x=sub.add_parser("fetch"); x.add_argument("--mailbox",default="INBOX"); x.add_argument("--uid",action="append",required=True); x.add_argument("--body-limit",type=int,default=0); x.add_argument("--text-limit",type=int,default=12000)
    x=sub.add_parser("search"); x.add_argument("--mailbox",default="INBOX"); x.add_argument("--query",nargs="+",required=True); x.add_argument("--limit",type=int,default=100)
    return p

def main():
    args=parser().parse_args(); client=None
    try:
        client=connect(); {"mailboxes":cmd_mailboxes,"list":cmd_list,"fetch":cmd_fetch,"search":cmd_search}[args.command](client) if args.command=="mailboxes" else {"list":cmd_list,"fetch":cmd_fetch,"search":cmd_search}[args.command](client,args)
        return 0
    except Exception as exc:
        print(json.dumps({"ok":False,"error":f"{exc.__class__.__name__}: {exc}"},ensure_ascii=False),file=sys.stderr); return 2
    finally:
        if client:
            try: client.logout()
            except Exception: pass

if __name__=="__main__": raise SystemExit(main())
