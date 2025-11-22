# Automatyczna instalacja backendu dla Windows
# Użycie: .\install-windows.ps1

Write-Host "🚀 Instalacja backendu Biblioteki dla Windows" -ForegroundColor Green
Write-Host ""

# Sprawdź czy jesteśmy w folderze backend
if (-not (Test-Path "requirements-windows.txt")) {
    Write-Host "❌ Błąd: Uruchom ten skrypt z folderu backend/" -ForegroundColor Red
    Write-Host "Przykład: cd backend && .\install-windows.ps1" -ForegroundColor Yellow
    exit 1
}

# Sprawdź czy venv istnieje
if (-not (Test-Path "venv")) {
    Write-Host "📦 Tworzenie środowiska wirtualnego..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Błąd podczas tworzenia venv" -ForegroundColor Red
        exit 1
    }
}

# Aktywuj venv
Write-Host "🔧 Aktywacja środowiska wirtualnego..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Zaktualizuj pip
Write-Host "⬆️  Aktualizacja pip, wheel i setuptools..." -ForegroundColor Cyan
python -m pip install --upgrade pip wheel setuptools --quiet

# Instaluj pakiety
Write-Host "📚 Instalacja pakietów (może potrwać 2-3 minuty)..." -ForegroundColor Cyan
pip install -r requirements-windows.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Instalacja zakończona pomyślnie!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Następne kroki:" -ForegroundColor Yellow
    Write-Host "1. Skopiuj .env.example do .env: copy .env.example .env"
    Write-Host "2. Edytuj .env i zmień SECRET_KEY"
    Write-Host "3. Zainicjuj bazę: python init_db.py"
    Write-Host "4. Uruchom serwer: python -m uvicorn app.main:app --reload"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Wystąpił błąd podczas instalacji" -ForegroundColor Red
    Write-Host "Sprawdź komunikaty błędów powyżej" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Jeśli problem dotyczy konkretnego pakietu:" -ForegroundColor Cyan
    Write-Host "   - Przeczytaj WINDOWS_INSTALL_GUIDE.md"
    Write-Host "   - Lub użyj Anacondy: https://www.anaconda.com/download"
    Write-Host ""
}
