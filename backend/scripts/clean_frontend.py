import re
from pathlib import Path

path = Path(r"D:\Github Projects\AI Frontent -Razorpay project\src\components\disputes\CaseMerchantControlCenter.tsx")
if path.exists():
    text = path.read_text(encoding="utf-8", errors="replace")

    # Replace character glitches
    replacements = [
        ("• ID:", "• ID:"),
        ("A ID:", "• ID:"),
        ("A Approved", "• Approved"),
        ("✓ APPROVED", "✓ APPROVED"),
        ("• PENDING APPROVAL", "• PENDING APPROVAL"),
        ("📝 Manual Evidence Entry", "📝 Manual Evidence Entry"),
        ("📁 Upload Document (PDF / Image)", "📁 Upload Document (PDF / Image)"),
        ("⚡ AI response updated", "⚡ AI response updated"),
        ("Edit Response ✏️", "Edit Response ✏️"),
        ("💡 Note:", "💡 Note:"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # General regex cleanups
    text = re.sub(r'[\ufffd]+', '', text)
    text = re.sub(r'A\s*ID:', '• ID:', text)
    text = re.sub(r'A\s*Approved', '• Approved', text)

    path.write_text(text, encoding="utf-8")
    print("Cleaned CaseMerchantControlCenter.tsx successfully.")
