test:
    uv run --with pydantic --with pydantic-settings --with python-dotenv --with pyyaml --with pytest pytest -q

# Confirma, no container em execução, que o cliente de uso do Agent Index
# herdado da imagem base está em execução. Não revela valores de credenciais.
check-agent-index:
    docker compose exec -T agent sh -ec 'reporter="$$(ps -eo pid=,args= | grep -E "[Aa]gent[ _-]?[Ii]ndex|[Uu]sage[ _-]?[Rr]eporter" || true)"; test -n "$$reporter" || { echo "Cliente do Agent Index não está ativo." >&2; exit 1; }; printf "%s\\n" "$$reporter"; echo "Cliente do Agent Index ativo."'
