Get-Content .env | Where-Object { $_ -notmatch '^\s*#' -and $_.Trim() -ne '' } | ForEach-Object {
    $splitLine = $_.Split('=')
    $varName = $splitLine[0].Trim()
    $varValue = $splitLine[1].Trim()
    [System.Environment]::SetEnvironmentVariable($varName, $varValue)
}