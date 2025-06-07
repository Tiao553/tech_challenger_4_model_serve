locals {
  database_to_paths = {
    "dl-raw-zone"      = "s3://tech-challanger-4-prd-raw-zone-593793061865/*"
    "dl-delivery-zone" = "s3://tech-challanger-4-prd-delivery-zone-593793061865/*"
  }
}


resource "aws_glue_crawler" "glue_crawler" {
  count = length(var.database_names) # Cria um crawler para cada banco de dados

  name          = "${local.prefix}-${var.database_names[count.index]}-crawler"
  database_name = var.database_names[count.index]
  role          = aws_iam_role.glue_role.arn

  # Define os caminhos S3 fixos para cada banco de dados
  s3_target {
    path = lookup(
      local.database_to_paths,
      var.database_names[count.index],
      null # Retorna null se não houver mapeamento, o que causaria um erro
    )
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })

  tags = merge(
    local.common_tags
  )
}
