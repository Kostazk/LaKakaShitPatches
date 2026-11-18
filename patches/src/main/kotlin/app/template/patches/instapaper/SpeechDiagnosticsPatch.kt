package app.template.patches.instapaper

import app.morphe.patcher.Fingerprint
import app.morphe.patcher.extensions.InstructionExtensions.addInstructions
import app.morphe.patcher.patch.AppTarget
import app.morphe.patcher.patch.Compatibility
import app.morphe.patcher.patch.bytecodePatch

private const val SPEECH_ERROR =
    "Lcom/instapaper/android/texttospeech/network/SpeechRemoteSourceException;"

private object SpeechErrorMessageFingerprint : Fingerprint(
    strings = listOf("resources", "throwable", "getString(...)"),
    parameters = listOf("Landroid/content/res/Resources;", "Ljava/lang/Throwable;"),
    returnType = "Ljava/lang/String;"
)

/** Reveal the status already received by the client, without logging request data. */
@Suppress("unused")
val speechDiagnosticsPatch = bytecodePatch(
    name = "Show AI speech error details",
    description = "Shows the HTTP status hidden by the generic AI speech error. Does not grant server access.",
    default = false
) {
    compatibleWith(Compatibility(
        name = "Instapaper",
        packageName = "com.instapaper.android",
        targets = listOf(AppTarget(version = "6.5"))
    ))

    execute {
        // In 6.5 the two-argument resource mapper has three local registers.
        // Only v0/v1 are used here, and the original path receives untouched
        // parameters. No error-body text, article content or credentials appear.
        val method = SpeechErrorMessageFingerprint.method
        check(method.implementation!!.registerCount - 3 >= 2) {
            "The speech error mapper no longer has the expected local registers."
        }
        method.addInstructions(0, """
            instance-of v0, p2, Lcom/instapaper/android/util/files/CorruptAudioFileException;
            if-eqz v0, :speech_diagnostics_remote
            const-string v0, "AI speech: received or cached audio is invalid."
            return-object v0
            :speech_diagnostics_remote
            instance-of v0, p2, $SPEECH_ERROR
            if-eqz v0, :speech_diagnostics_original
            check-cast p2, $SPEECH_ERROR
            invoke-virtual {p2}, $SPEECH_ERROR->a()Ljava/lang/Integer;
            move-result-object v0
            if-eqz v0, :speech_diagnostics_no_status
            invoke-virtual {v0}, Ljava/lang/Integer;->toString()Ljava/lang/String;
            move-result-object v0
            const-string v1, "AI speech request failed: HTTP "
            invoke-virtual {v1, v0}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;
            move-result-object v0
            return-object v0
            :speech_diagnostics_no_status
            const-string v0, "AI speech request failed without an HTTP status."
            return-object v0
            :speech_diagnostics_original
            nop
        """.trimIndent())
    }
}
