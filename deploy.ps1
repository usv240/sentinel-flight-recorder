$PROJECT_ID = "orace-agent"
$REGION     = "us-central1"
$SERVICE    = "sentinel"
$IMAGE      = "gcr.io/$PROJECT_ID/$SERVICE"
$DIR        = $PSScriptRoot   # sentinel/ — Dockerfile + all deps are here

Write-Host "=== SENTINEL Cloud Run Deploy ===" -ForegroundColor Cyan
Write-Host "Project : $PROJECT_ID"
Write-Host "Service : $SERVICE"
Write-Host "Region  : $REGION"
Write-Host "Build from: $DIR"
Write-Host ""

# 1. Build and push image
Write-Host "Step 1/2: Building image..." -ForegroundColor Yellow
gcloud builds submit $DIR --tag $IMAGE --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed." -ForegroundColor Red; exit 1 }

# 2. Deploy to Cloud Run
Write-Host "Step 2/2: Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE `
  --image $IMAGE `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 1Gi `
  --cpu 1 `
  --timeout 300 `
  --concurrency 80 `
  --env-vars-file "$DIR\env-cloud.yaml" `
  --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) { Write-Host "Deploy failed." -ForegroundColor Red; exit 1 }

$URL = gcloud run services describe $SERVICE `
  --platform managed --region $REGION --project $PROJECT_ID `
  --format "value(status.url)"

Write-Host ""
Write-Host "=== DEPLOYED ===" -ForegroundColor Green
Write-Host "Live URL: $URL" -ForegroundColor Green
Write-Host "Full health check: $URL/api/health"
Write-Host "Demo: $URL/"
