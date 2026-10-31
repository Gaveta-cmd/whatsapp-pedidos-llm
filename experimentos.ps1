# Experimentos de ablação: treina varias versoes do modelo mudando UMA coisa por vez nos dados,
# para descobrir qual mudanca do v4 piorou o modelo (ver docs/DIARIO.md, secao 15).
#
# Uso (PowerShell, dentro da pasta do projeto), nomes separados por virgula:
#   powershell -ExecutionPolicy Bypass -File .\experimentos.ps1 A_controle_v3,B_caixa_v3,C_pontuacao_v3
#
# Variantes:
#   A_controle_v3    dados do v3 originais (recuperados do primeiro commit do git) + o treino de hoje
#   B_caixa_v3       dados do v4, mas com a caixa (maiusculas/minusculas) do v3
#   C_pontuacao_v3   dados do v4, mas com a pontuacao/separadores do v3
#   D_sem_v4         caixa e pontuacao do v3, mas com os 3.000 exemplos e as demais mudancas do v4
param([string[]]$Variantes = @("A_controle_v3"))

$ErrorActionPreference = "Continue"
$Variantes = $Variantes | ForEach-Object { $_ -split "," } | Where-Object { $_ }  # com -File, a virgula chega como texto unico
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force "outputs\exp" | Out-Null

function Preparar-Dados($nome) {
    $pasta = "data\variantes\$nome"
    if (Test-Path "$pasta\train.jsonl") { return }
    New-Item -ItemType Directory -Force $pasta | Out-Null
    switch ($nome) {
        "A_controle_v3" {
            git show 9efc1af:data/train.jsonl | Set-Content -Encoding utf8 "$pasta\train.jsonl"
            Copy-Item data\val.jsonl "$pasta\val.jsonl"
        }
        "B_caixa_v3" { & $py src\gerar_dados.py --n 3000 --seed 42 --manter-teste --caixa v3 --pontuacao v4 --saida $pasta }
        "C_pontuacao_v3" { & $py src\gerar_dados.py --n 3000 --seed 42 --manter-teste --caixa v4 --pontuacao v3 --saida $pasta }
        "E_gemeos" { & $py src\gerar_dados.py --n 4000 --seed 42 --manter-teste --caixa v4 --pontuacao v3 --gemeos --saida $pasta }
        "D_sem_v4" { & $py src\gerar_dados.py --n 3000 --seed 42 --manter-teste --caixa v3 --pontuacao v3 --saida $pasta }
        default { throw "variante desconhecida: $nome" }
    }
}

foreach ($v in $Variantes) {
    Write-Host ">>> $v"
    Preparar-Dados $v
    $adapter = "outputs\exp\$v"
    if (-not (Test-Path "$adapter\adapter_config.json")) {
        & $py -u -W ignore src\treinar.py --epocas 3 --dados "data\variantes\$v" --saida $adapter 2>&1 | Tee-Object -FilePath "outputs\exp\treino_$v.log"
        if (Test-Path "${adapter}_ckpt") { Remove-Item -Recurse -Force "${adapter}_ckpt" }
    }
    if (-not (Test-Path "$adapter\adapter_config.json")) { Write-Host "treino de $v falhou"; continue }
    & $py -u -W ignore src\robustez.py --adapter $adapter --nome "exp_$v" 2>&1 | Tee-Object -FilePath "outputs\exp\robustez_$v.log"
    & $py -u -W ignore src\avaliar_modelo.py --adapter $adapter --nome "exp_$v" 2>&1 | Tee-Object -FilePath "outputs\exp\avaliacao_$v.log"
}
Write-Host "experimentos terminados"
