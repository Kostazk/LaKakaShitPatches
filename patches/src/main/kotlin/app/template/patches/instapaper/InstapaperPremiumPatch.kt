package app.template.patches.instapaper

import app.morphe.patcher.extensions.InstructionExtensions.addInstructions
import app.morphe.patcher.extensions.InstructionExtensions.instructions
import app.morphe.patcher.extensions.InstructionExtensions.removeInstructions
import app.morphe.patcher.patch.bytecodePatch
import app.template.patches.shared.Constants.INSTAPAPER_COMPATIBILITY

@Suppress("unused")
val unlockPremiumPatch = bytecodePatch(
    name = "Unlock Premium",
    description = "Enables local premium features. AI speech and other server services still require server-side access.",
    default = true
) {
    compatibleWith(INSTAPAPER_COMPATIBILITY)

    execute {
        // A missing fingerprint must fail the patch instead of reporting success
        // without changing anything. The getter still matches Instapaper 6.5.
        PremiumCheckFingerprint.method.apply {
            removeInstructions(0, instructions.count())
            addInstructions(0, "const-string v0, \"1\"\nreturn-object v0")
        }
    }
}
