resource "azurerm_storage_account" "storage" {
  name                            = var.storage_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  public_network_access_enabled   = true # TODO: Set to false when we have a VNet
  default_to_oauth_authentication = true
  is_hns_enabled                  = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.storage.id

  rule {
    name    = "delete-old-logs"
    enabled = true
    filters {
      prefix_match = ["insights-logs-", "insights-metrics-"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }
}

resource "azurerm_storage_container" "container" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# Add a delay to allow for the storage to be created 
resource "null_resource" "wait_for_storage_account" {
  provisioner "local-exec" {
    command = "sleep 120"
  }
  depends_on = [var.keyvault_id, azurerm_storage_account.storage, var.wait_for_propagation]
}

# Create a secret in the Key Vault
resource "azurerm_key_vault_secret" "storage_key" {
  name         = "STORAGE-KEY"
  value        = azurerm_storage_account.storage.primary_access_key
  key_vault_id = var.keyvault_id

  depends_on = [null_resource.wait_for_storage_account]
}

# Assign "Key Vault Crypto Service Encryption User" role
resource "azurerm_role_assignment" "storage_key_vault_crypto_user" {
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Crypto Service Encryption User"
  principal_id         = azurerm_storage_account.storage.identity[0].principal_id

  depends_on = [null_resource.wait_for_storage_account]
}

# Assign "Key Vault Secrets User" role
resource "azurerm_role_assignment" "storage_key_vault_secrets_user" {
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_storage_account.storage.identity[0].principal_id

  depends_on = [null_resource.wait_for_storage_account]
}

# Add a delay to allow for the permissions to propagate
resource "null_resource" "wait_for_storage_permission_propagation" {
  provisioner "local-exec" {
    command = "sleep 120"
  }
  depends_on = [
    null_resource.wait_for_storage_account,
    azurerm_role_assignment.storage_key_vault_crypto_user,
    azurerm_role_assignment.storage_key_vault_secrets_user
  ]
}

# Update storage account to use the Key Vault Key for encryption
# SC-13: Customer-managed keys for enhanced encryption control
resource "azurerm_storage_account_customer_managed_key" "storage_cmk" {
  storage_account_id = azurerm_storage_account.storage.id
  key_vault_id       = var.keyvault_id
  key_name           = var.cmk_name

  depends_on = [null_resource.wait_for_storage_permission_propagation]
}
