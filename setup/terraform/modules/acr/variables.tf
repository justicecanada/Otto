variable "acr_name" {
  description = "The name of the ACR"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "location" {
  description = "The Azure region for resource deployment"
  type        = string
}

variable "acr_sku" {
  description = "The SKU (pricing tier) of the ACR"
  type        = string
  default     = "Basic"
}

variable "tags" {
  description = "A mapping of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

variable "acr_publisher_object_ids" {
  description = "The list of object IDs of the ACR publishers Azure AD groups"
  type        = list(string)
}

variable "keyvault_id" {
  description = "The ID of the Key Vault"
  type        = string
}
