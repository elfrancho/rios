# Manda el reel de los 30 mil a francho14@gmail.com por Outlook.
$dir = 'C:\Users\FRANCISCO\Documents\Pancho\rios\festejo30k'
$ol = New-Object -ComObject Outlook.Application
$m = $ol.CreateItem(0)
$m.To = 'francho14@gmail.com'
$m.Subject = 'Reel 30 mil seguidores (sin audio, para ponerle música)'
$texto = Get-Content (Join-Path $dir 'texto.txt') -Raw -Encoding utf8
$m.Body = "Adjunto el video (24 s, sin audio: la música la ponés en Instagram).`r`n`r`nMúsica sugerida: «Kilómetro 11» (chamamé instrumental de Tránsito Cocomarola). Otra opción: «El cosechero» (Ramón Ayala), que nombra al Paraná. Buscalas en la biblioteca de música de Instagram al subirlo.`r`n`r`nTexto para pegar:`r`n`r`n$texto`r`nFrancisco"
$m.Attachments.Add((Join-Path $dir 'reel_30mil.mp4')) | Out-Null
$m.Send()
Add-Content -Path 'C:\Users\FRANCISCO\Documents\Pancho\rios\historias\partes\envios.log' -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm') reel 30 mil enviado a francho14@gmail.com" -Encoding utf8
'ok'
