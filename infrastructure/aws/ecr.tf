# Criar um repositório ECR para a Lambda
resource "aws_ecr_repository" "lambda_repo" {
  name                 = "${local.prefix}-lambda-repo-tech-challenger-4-${terraform.workspace}"
  image_tag_mutability = "MUTABLE" # Permite modificar tags de imagens (pode ser configurado como IMMUTABLE se necessário)

  # Tags opcionais para organização
  tags = merge(
    local.common_tags,
  )
}

