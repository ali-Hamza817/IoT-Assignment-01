# Builds the assignment report.
#   Ali Hamza_IoT_Assignment 1.pdf                       final submission (answers only)  -> repository root
#   report\IT863_Assignment01_Solution_With_Questions.pdf  same report with the question text (local copy)
#
#   .\build.ps1             -> compile (runs the simulations first if their outputs are missing)
#   .\build.ps1 -Simulate   -> always re-run every simulation first (about 2 minutes)
param([switch]$Simulate)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Simulate -or -not (Test-Path "$root\media\frames\q2_rtscts.pdf") -or -not (Test-Path "$root\media\figures\q1_layout.pdf")) {
    Push-Location "$root\simulations"
    python run_all.py
    Pop-Location
}

function Compile($source, $job) {
    foreach ($pass in 1, 2) {
        pdflatex -interaction=nonstopmode -halt-on-error "-jobname=$job" $source | Out-Null
    }
    if ($LASTEXITCODE -ne 0) { throw "LaTeX failed - see report\$job.log" }
}

Push-Location "$root\report"
try {
    Compile "answers_only.tex" "IT863_Assignment01_Solution_Answers_Only"
    Compile "main.tex" "IT863_Assignment01_Solution_With_Questions"
    Copy-Item IT863_Assignment01_Solution_Answers_Only.pdf "$root\Ali Hamza_IoT_Assignment 1.pdf" -Force
} finally {
    Pop-Location
}
Write-Host "Final (answers only): $root\Ali Hamza_IoT_Assignment 1.pdf"
Write-Host "With questions:       $root\report\IT863_Assignment01_Solution_With_Questions.pdf"
