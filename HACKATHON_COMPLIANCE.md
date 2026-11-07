# Plow × Hermes Hackathon — Compliance

Última verificação do estado do repositório: **2026-11-07**.

Este checklist separa o que está comprovado no GitHub e no código do que depende de serviços externos, credenciais de produção ou evidência que ainda não foi publicada. Um item marcado como não verificado não deve ser apresentado como concluído.

## Requisitos identificados

- Agente baseado em Hermes e integrado ao ecossistema Plow.
- Plow Latch como camada de execução local e Plow Chat/iMessage como interface de interação.
- Repositório público e licença open source.
- Registro do agente no AI Worth Using Agent Index e reporter de uso ativo.
- Workflow de produto demonstrável com o agente real.
- Casos de uso publicados e demonstração audiovisual.

## Estado verificado

| Requisito | Estado em 2026-11-07 | Evidência / próxima ação |
|---|---|---|
| Runtime Hermes | **PASS — código** | O Dockerfile deriva da imagem Plow/Hermes fixada por digest e inicia os serviços Hermes via s6-overlay. Isso comprova a implementação no repositório, não uma execução de produção nesta auditoria. |
| Integração Plow/Latch | **PASS — código** | `plow-init.py`, configuração MCP Plow, plugin `plow_chat` e skills documentam e implementam o caminho de integração. |
| Repositório público | **PASS** | A API do GitHub retornou `private: false` para `Rodrooj/product-developer-assistant` em 2026-11-07. |
| Licença open source | **PASS** | O arquivo `LICENSE` contém a licença MIT; README e arquivo de licença usam a mesma identificação. |
| Workflow principal de pesquisa | **IMPLEMENTADO NO REPOSITÓRIO** | A skill `web-research` e a primeira dobra do README definem pesquisa web/netnografia → dossiê Markdown auditável. A apresentação externa do Agent Index ainda precisa ser atualizada. |
| Agent Index: registro deste agente | **NÃO VERIFICADO** | Não foi possível confirmar o Agent Index ID ou a página de registro com acesso ao repositório. Registrar/confirmar o ID no painel externo e documentar somente um identificador não secreto. |
| Agent Index: reporter de uso | **NÃO VERIFICADO** | A imagem base é identificada no Dockerfile, mas esta auditoria não inspecionou o runtime Plow em produção nem observou uma comunicação autenticada com a API do Agent Index. A existência de um processo ou uma busca por nome não comprova envio e aceitação de eventos. Exigir self-check/dry-run oficial ou evidência equivalente, sem expor credenciais. |
| Casos de uso publicados no Agent Index | **NÃO VERIFICADO** | O inventário em `docs/USE_CASES.md` é documentação do repositório, não prova de publicação no Agent Index. Confirmar na página pública do agente. |
| Casos de uso com evidência independente | **PARCIAL** | A issue #10 é um registro público de issue encerrada. Os usos de Pages e briefing de e-mail permanecem relatos operacionais sem artefatos públicos/redigidos vinculados. |
| Vídeo demo ponta a ponta | **PENDENTE** | Gravar uma demonstração real no Plow Chat/Latch, com resultado observável e link público. Nenhum vídeo foi confirmado nesta auditoria. |
| Participação/uso na janela da competição | **NÃO VERIFICADO** | Depende de dados e regras no serviço externo; não inferir instalações, usuários ativos ou tokens a partir do código do repositório. |

## Segurança e integridade

- Nunca commitar `plow-credentials`, tokens, sessões, arquivos `.env` ou dados privados.
- Preservar a inicialização fail-closed do Plow enquanto a variante hospedada depender desse contrato.
- Não tratar uma inspeção de processos como confirmação de reporte ao Agent Index.
- Não publicar documentos Pages, e-mails ou logs que contenham dados pessoais; produzir artefatos redigidos e autorizados antes de vinculá-los.
- A implementação deste repositório continua sendo a variante integrada ao Plow. O desacoplamento para execução autônoma com FoxMCP/modelo local é trabalho separado e não deve ser confundido com os requisitos de conformidade acima.

## Próximas ações externas

1. Confirmar o Agent Index ID e a configuração do reporter no ambiente Plow real.
2. Executar o diagnóstico oficial do reporter e guardar a saída sem segredos.
3. Atualizar a descrição pública do Agent Index para o workflow principal.
4. Publicar pelo menos três casos de uso com artefatos públicos verificáveis e um vídeo demo funcional.
5. Confirmar os dados da janela de uso diretamente no Agent Index.

## Base desta verificação

A verificação de repositório público e branches/issues foi realizada pela API GitHub em 2026-11-07. O estado do reporter, o registro e a publicação de casos no Agent Index dependem de acesso ao serviço e ao runtime externos e, por isso, permanecem explicitamente não verificados.
