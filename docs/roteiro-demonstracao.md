# Roteiro de demonstração do DueFlow

Este roteiro valida o fluxo principal exclusivamente pelo painel, depois que API,
worker e frontend estiverem em execução e o usuário administrador tiver sido criado.
O provider deve permanecer como `fake` durante a demonstração.

## Preparação

1. Entre no painel com o administrador local.
2. Em **Configurações**, mantenha a automação ativa e o intervalo em 2 minutos.
3. Confirme que o indicador lateral apresenta **Ativa**.

## Fluxo principal

1. Acesse **Clientes** e cadastre um cliente ativo com um WhatsApp fictício válido.
2. No detalhe do cliente, escolha **Nova cobrança**.
3. Cadastre uma cobrança pendente com vencimento hoje ou dentro da janela de aviso.
4. Volte à **Visão geral** e selecione **Verificar agora**.
5. Observe a confirmação de que a verificação foi adicionada à fila e aguarde o
   estado terminal exibido pelo polling.
6. Acesse **Execuções da automação**, abra a execução criada e confira:
   origem, linha do tempo, política vencedora, motivo da decisão e resultado simulado.
7. Acesse **Histórico de mensagens**, abra a tentativa e confira a mensagem,
   o provider simulado e os vínculos para cliente, cobrança e execução.
8. Volte à cobrança e execute **Verificar agora** novamente. Confirme no detalhe
   técnico que a mensagem não foi duplicada.
9. Marque a cobrança como paga e confirme que seu estado deixa de permitir novos avisos.

## Automação recorrente

1. Cadastre outra cobrança elegível sem usar **Verificar agora**.
2. Aguarde o intervalo configurado.
3. Confirme pela Visão geral que o lembrete foi processado.
4. Abra **Execuções da automação** e identifique a origem automática.
5. Pause a automação em **Configurações** e confirme a mudança no indicador lateral.

## Estados alternativos

- Use os filtros e a paginação, recarregue a página e confirme que a URL preserva o estado.
- Consulte uma listagem sem resultados e valide a orientação exibida.
- Interrompa temporariamente a API e use **Tentar novamente** em uma tela com erro.
- Reduza a largura da janela e percorra menu, tabelas, formulários e diálogos por teclado.
- Troque a senha, confirme o encerramento da sessão e entre novamente com a nova senha.

## Critérios de aprovação

- Nenhuma etapa de negócio depende do Swagger.
- A interface distingue dados de negócio das informações técnicas.
- Loading, vazio, erro, confirmação e sucesso têm retorno visível.
- O polling para ao alcançar estados terminais e não trabalha em segundo plano.
- Nenhuma credencial, token ou telefone completo aparece em logs ou na gravação.
