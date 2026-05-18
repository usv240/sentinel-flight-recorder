$PROJECT_ID = "orace-agent"
$REGION = "us-central1"
$SERVICE = "sentinel"
$IMAGE = "gcr.io/" + $PROJECT_ID + "/" + $SERVICE
$PARENT = Split-Path -Parent $PSScriptRoot

Write-Host "Deploying SENTINEL from parent directory (includes fivetran-mcp)..."

# Build from parent directory so Dockerfile can COPY fivetran-mcp/
gcloud builds submit $PARENT --tag $IMAGE --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed."; exit 1 }

gcloud run deploy $SERVICE --image $IMAGE --platform managed --region $REGION --allow-unauthenticated --port 8080 --memory 512Mi --env-vars-file env-cloud.yaml --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "Deploy failed."; exit 1 }

$URL = gcloud run services describe $SERVICE --platform managed --region $REGION --project $PROJECT_ID --format "value(status.url)"
Write-Host "DONE. URL: " + $URL
