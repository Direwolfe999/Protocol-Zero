import streamlit as st
from datetime import datetime

@st.fragment(run_every=5)
def tick():
    st.write(datetime.now())

tick()
st.write("Main app")
