# Criar Lambda Function
resource "aws_lambda_function" "crawler_lambda" {
  function_name = "${local.prefix}-api-stock-prediction"
  description   = "Função Lambda para crawler de ações do Yahoo Finance"
  role          = aws_iam_role.lambda_decompress.arn
  package_type  = "Image"
  image_uri     = "593793061865.dkr.ecr.us-east-1.amazonaws.com/tech-challanger-4-prd-lambda-repo-tech-challenger-4-prd:latest"
  timeout       = 900
  memory_size   = 1024
  architectures = ["x86_64"]

  tags = merge(
    local.common_tags,
  )
  
  environment {
    variables = {
      API_GATEWAY_ROOT_PATH = "/prod"
      STAGE                 = "prod"
    }
  }

  depends_on = [aws_ecr_repository.lambda_repo]
}
