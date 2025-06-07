# Define a API HTTP. A configuração de CORS aqui é uma boa prática
# e simplifica o gerenciamento, pois o API Gateway responde automaticamente
# às solicitações OPTIONS de pré-verificação (preflight).
resource "aws_apigatewayv2_api" "crawler_api" {
  name          = "crawler-fastapi"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins     = ["*"] # Em produção, restrinja para seus domínios
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    allow_credentials = false
    max_age           = 3600
  }
}

# Cria a integração entre a API e a função Lambda.
# 'AWS_PROXY' é o tipo de integração que passa o request completo
# para o Lambda, permitindo que frameworks como o FastAPI gerenciem o roteamento.
resource "aws_apigatewayv2_integration" "crawler_lambda_integration" {
  api_id                 = aws_apigatewayv2_api.crawler_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.crawler_lambda.invoke_arn
  payload_format_version = "2.0"
}

# Rota "catch-all" (pega-tudo). Este é o recurso mais importante para o roteamento.
# O `route_key = "ANY /{proxy+}"` captura qualquer método (GET, POST, etc.)
# em qualquer caminho sob o estágio (ex: /prod/docs, /prod/users/123, e até mesmo /prod/).
# Ele encaminha tudo para a integração Lambda, onde o FastAPI assume o controle.
resource "aws_apigatewayv2_route" "any_proxy" {
  api_id    = aws_apigatewayv2_api.crawler_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.crawler_lambda_integration.id}"
}

# ESTE É O RECURSO-CHAVE PARA O SEU REQUISITO.
# A definição de um estágio com `name = "prod"` cria o prefixo de caminho /prod na URL de invocação.
# É exatamente este prefixo que o FastAPI precisa conhecer através do parâmetro `root_path="/prod"`.
# Isso garante que a documentação interativa (/docs) e outras URLs geradas pela aplicação
# incluam o prefixo do estágio corretamente[2][8].
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.crawler_api.id
  name        = "prod"
  auto_deploy = true
}

# Permissão necessária para que o API Gateway possa invocar sua função Lambda.
# O `source_arn` garante que apenas esta API específica possa acionar a função.
resource "aws_lambda_permission" "allow_apigw_to_invoke_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crawler_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.crawler_api.execution_arn}/*/*"
}
