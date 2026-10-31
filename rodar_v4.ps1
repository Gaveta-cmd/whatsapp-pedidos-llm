# Roda o v4 inteiro, do treino até as avaliações. Pode ser interrompido e repetido: retoma do último checkpoint.
#
# Como usar (PowerShell, dentro da pasta do projeto):
#   powershell -ExecutionPolicy Bypass -File .\rodar_v4.ps1
#
# Antes: feche jogos e programas pesados (Wallpaper Engine, etc.). O treino usa quase toda a memória da placa.
# Duração aproximada com a placa livre: treino 10-20 min + avaliações 10 min.

# "Continue" (e nao "Stop"): o PowerShell 5.1 trata qualquer aviso do Python no stderr como erro fatal quando usamos 2>&1.
# Os erros reais sao pegos pelas checagens explicitas abaixo.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $py)) { throw "Ambiente .venv não encontrado. Veja o README (seção 'Como rodar')." }
if (-not (Test-Path "data\train.jsonl")) { & $py src\gerar_dados.py --n 3000 --seed 42 --manter-teste }

# 1) Treino. Se já existe checkpoint, continua de onde parou.
$temCheckpoint = (Test-Path "outputs\checkpoints") -and (Get-ChildItem "outputs\checkpoints" -Filter "checkpoint-*" -ErrorAction SilentlyContinue)
if ($temCheckpoint) { Write-Host ">> Retomando do último checkpoint"; & $py -u -W ignore src\treinar.py --epocas 3 --retomar 2>&1 | Tee-Object -Append -FilePath outputs\treino_v4.log }
else { Write-Host ">> Treino do zero"; & $py -u -W ignore src\treinar.py --epocas 3 2>&1 | Tee-Object -FilePath outputs\treino_v4.log }
if (-not (Test-Path "outputs\lora-qwen1.5b\adapter_config.json")) { throw "Treino não terminou: adapter não foi salvo." }

# 2) Critério de aceitação (definido ANTES do resultado): >= 34/40 nas 4 formas e diferença <= 3.
& $py -u -W ignore src\robustez.py --nome v4 2>&1 | Tee-Object -FilePath outputs\robustez_v4.log

# 3) Teste sintético (100 mensagens), para ver se o v4 não piorou no que já funcionava.
& $py -u -W ignore src\avaliar_modelo.py --nome lora_qwen_v4 2>&1 | Tee-Object -FilePath outputs\avaliacao_v4.log

# 4) Gráficos e prints atualizados.
& $py -W ignore src\gerar_evidencias.py

Write-Host ""
Write-Host "Pronto. Veja outputs\resultados\robustez_v4.json e lora_qwen_v4.json."
Write-Host "Se 'aprovado' for true em robustez_v4.json, escreva o lote novo de mensagens (data\mensagens_finais_v4.txt) e me chame."
