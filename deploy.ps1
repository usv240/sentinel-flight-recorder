$PROJECT_ID = "orace-agent"
$REGION = "us-central1"
$SERVICE = "sentinel"
$IMAGE = "gcr.io/" + $PROJECT_ID + "/" + $SERVICE

Write-Host "Deploying SENTINEL to Cloud Run (separate from ORACLE)..."

gcloud builds submit --tag $IMAGE --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed."; exit 1 }

gcloud run deploy $SERVICE --image $IMAGE --platform managed --region $REGION --allow-unauthenticated --port 8080 --memory 512Mi --env-vars-file env-cloud.yaml --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "Deploy failed."; exit 1 }

$URL = gcloud run services describe $SERVICE --platform managed --region $REGION --project $PROJECT_ID --format "value(status.url)"
Write-Host "DONE. URL: " + $URL
