param(
    [string]$SdkRoot = $env:ANDROID_HOME,
    [string]$JdkRoot = $env:JAVA_HOME,
    [string]$SigningKey,
    [string]$SigningAlias = 'study-local'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (!$SdkRoot -or !$JdkRoot) { throw 'ANDROID_HOME과 JAVA_HOME 또는 -SdkRoot와 -JdkRoot를 지정하세요.' }
$sdk = (Resolve-Path -LiteralPath $SdkRoot).Path
$jdk = (Resolve-Path -LiteralPath $JdkRoot).Path
$buildTools = (Get-ChildItem -LiteralPath (Join-Path $sdk 'build-tools') -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'apksigner.bat') } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$platform = Join-Path $sdk 'platforms/android-35/android.jar'
if (!$buildTools -or !(Test-Path -LiteralPath $platform)) {
    throw 'Android SDK Platform 35와 Android SDK Build-Tools를 설치하세요.'
}
$env:JAVA_HOME = $jdk
$env:Path = (Join-Path $jdk 'bin') + ';' + $env:Path
$build = Join-Path $PSScriptRoot 'build'
$classes = Join-Path $build 'classes'
$dex = Join-Path $build 'dex'
New-Item -ItemType Directory -Path $classes,$dex -Force | Out-Null
function Invoke-Build([scriptblock]$Step) {
    & $Step
    if ($LASTEXITCODE -ne 0) { throw "Build step exited $LASTEXITCODE." }
}
Invoke-Build { javac -encoding utf8 -source 8 -target 8 -classpath $platform -d $classes StudyActivity.java }
$classJar = Join-Path $build 'classes.jar'
Invoke-Build { jar cf $classJar -C $classes . }
Invoke-Build { & (Join-Path $buildTools 'd8.bat') --min-api 28 --lib $platform --output $dex $classJar }
$raw = Join-Path $build 'raw.apk'
$aligned = Join-Path $build 'aligned.apk'
$release = Join-Path $build 'study-assist.apk'
$aapt = Join-Path $buildTools 'aapt2.exe'
$compiledResources = Join-Path $build 'resources.zip'
Invoke-Build { & $aapt compile --dir res -o $compiledResources }
Invoke-Build { & $aapt link -I $platform --manifest AndroidManifest.xml -o $raw -R $compiledResources --auto-add-overlay }
Invoke-Build { jar uf $raw -C $dex classes.dex }
Invoke-Build { & (Join-Path $buildTools 'zipalign.exe') -f 4 $raw $aligned }
$signer = if ($SigningKey) { $SigningKey } else { Join-Path $build 'local-test.jks' }
if ($SigningKey -and !$env:STUDY_APK_STORE_PASS) { throw 'STUDY_APK_STORE_PASS를 설정하세요.' }
if (!$env:STUDY_APK_STORE_PASS) { $env:STUDY_APK_STORE_PASS = 'android' }
if (-not (Test-Path -LiteralPath $signer)) {
    Invoke-Build { keytool -genkeypair -keystore $signer -storepass:env STUDY_APK_STORE_PASS -keypass:env STUDY_APK_STORE_PASS -alias $SigningAlias -dname 'CN=Study Assist' -keyalg RSA -validity 3650 }
}
Invoke-Build { & (Join-Path $buildTools 'apksigner.bat') sign --ks $signer --ks-key-alias $SigningAlias --ks-pass env:STUDY_APK_STORE_PASS --out $release $aligned }
Invoke-Build { & (Join-Path $buildTools 'apksigner.bat') verify --verbose $release }
Get-Item -LiteralPath $release | Select-Object FullName,Length
