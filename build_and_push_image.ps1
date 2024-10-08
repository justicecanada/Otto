# Ensure Azure login and correct subscription selection
az login
Write-Host "Available subscriptions:"
az account list --query "[].{SubscriptionId:id, Name:name}" --output table
$SUBSCRIPTION_ID = Read-Host -Prompt "Enter the Subscription ID you want to use"
az account set --subscription $SUBSCRIPTION_ID

# Prompt for inputs
Write-Host "Available container registries:"
az acr list --query "[].{Name:name, ResourceGroup:resourceGroup}" --output table
$REGISTRY_NAME = Read-Host -Prompt "Enter the registry name you want to use"

$VERSION = Read-Host -Prompt "Enter the version number (e.g., v1.0.0)"

# Get the latest Git commit hash dynamically
$GITHUB_HASH = & git rev-parse HEAD

# Generate build number
$BUILD_NUMBER = Get-Date -Format "yyyyMMdd-HHmmss"

# Create version.yaml content
$versionYaml = @"
version: $VERSION
github_hash: $GITHUB_HASH
build_date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

# Write version.yaml to a temporary file
$tempFile = New-TemporaryFile
$versionYaml | Out-File -FilePath $tempFile -Encoding utf8

# Copy version.yaml to the build context directory
Copy-Item -Path $tempFile -Destination "./django/version.yaml"

# Prepare image name and tag
$IMAGE_NAME = "$($REGISTRY_NAME).azurecr.io/otto"
$SPECIFIC_TAG = "$VERSION-$BUILD_NUMBER"

# Inform the user that, if the image doesn't exist in the Docker cache, they will need to be off the JUS network to pull the base image
Write-Host "If the image doesn't exist in the Docker cache, you will need to be off the JUS network to pull the base image."
$continue = Read-Host -Prompt "Do you want to continue? (y/N)"
if ($continue -ne "y") {
    exit
}

# Build Docker image
docker build -t ${IMAGE_NAME}:${SPECIFIC_TAG} -f ./django/Dockerfile ./django

# Tag Docker image for ACR
docker tag ${IMAGE_NAME}:${SPECIFIC_TAG} ${IMAGE_NAME}:latest

# Login to ACR
az acr login --name $REGISTRY_NAME

# Push Docker image to ACR
docker push ${IMAGE_NAME}:${SPECIFIC_TAG}
docker push ${IMAGE_NAME}:latest

# Optionally, you can clean up the temporary file
Remove-Item -Path $tempFile
