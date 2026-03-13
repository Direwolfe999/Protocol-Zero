"""Hugging Face Spaces entrypoint.

Spaces Streamlit SDK expects app.py by default.
Reuse the same startup path used by streamlit_app.py.
"""

import streamlit_app  # noqa: F401
