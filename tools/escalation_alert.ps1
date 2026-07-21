# Escalation alert: Windows toast + sound. Launched detached by the harness
# (runlog._alert) with context in env vars; must never block or throw loudly.
# Swap or extend this script to change how escalations reach a human --
# the harness contract is only "run alert_cmd with LLMPLAYS_* in the env".
$kind = if ($env:LLMPLAYS_KIND) { $env:LLMPLAYS_KIND } else { "unknown" }
$detail = if ($env:LLMPLAYS_DETAIL) { $env:LLMPLAYS_DETAIL } else { "" }
$run = if ($env:LLMPLAYS_RUN) { Split-Path $env:LLMPLAYS_RUN -Leaf } else { "?" }

try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
        [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $texts = $xml.GetElementsByTagName("text")
    $texts.Item(0).AppendChild($xml.CreateTextNode("llm-plays ${run}: $kind")) | Out-Null
    $texts.Item(1).AppendChild($xml.CreateTextNode($detail)) | Out-Null
    $toast = New-Object Windows.UI.Notifications.ToastNotification($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("llm-plays").Show($toast)
} catch {
    # toast API unavailable: fall back to a console beep so SOMETHING happens
    try { [Console]::Beep(880, 400); [Console]::Beep(660, 400) } catch {}
}
