"""Streamlit entry point (Slice 4).

`streamlit run main.py` boots the multipage app: Connect → Dashboard →
Trace → History.
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="OpsScout", page_icon="🌦", layout="wide")
    st.title("OpsScout")
    st.caption("Use the sidebar to navigate: Connect → Dashboard → Trace → History.")


if __name__ == "__main__":
    main()
