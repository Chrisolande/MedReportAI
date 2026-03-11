"""CSS injection for MedReportAI Studio."""

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@400;600;700;800&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">

        <style>
        :root {
            --bg:        #0a0d0f;
            --bg1:       #0f1418;
            --bg2:       #141b22;
            --bg3:       #1a2430;
            --panel:     #111820;
            --border:    rgba(74,222,128,0.12);
            --border2:   rgba(74,222,128,0.25);
            --border3:   rgba(74,222,128,0.45);
            --green:     #4ade80;
            --green2:    #22c55e;
            --green-dim: rgba(74,222,128,0.08);
            --amber:     #fbbf24;
            --red:       #f87171;
            --cyan:      #22d3ee;
            --ink:       #e2ead4;
            --ink2:      #a8b8a0;
            --muted:     #5a7060;
            --mono:      'Syne Mono', monospace;
            --sans:      'Syne', sans-serif;
            --serif:     'DM Serif Display', serif;
            --glow:      0 0 20px rgba(74,222,128,0.15);
            --glow2:     0 0 40px rgba(74,222,128,0.08);
        }

        html, body, .stApp {
            background-color: var(--bg) !important;
            color: var(--ink);
            font-family: var(--sans);
        }

        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0,0,0,0.04) 2px,
                rgba(0,0,0,0.04) 4px
            );
            pointer-events: none;
            z-index: 9999;
        }

        #MainMenu, footer, header, [data-testid="stToolbar"] { display: none !important; }
        .block-container { padding: 1.5rem 2rem 3rem !important; max-width: 1200px !important; }

        [data-testid="stSidebar"] {
            background: var(--panel) !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"]::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--green), transparent);
        }
        [data-testid="stSidebar"] * { color: var(--ink2) !important; }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            font-family: var(--mono) !important;
            color: var(--green) !important;
            letter-spacing: 0.05em !important;
        }
        [data-testid="stSidebar"] .stTextArea textarea {
            background: var(--bg2) !important;
            border: 1px solid var(--border) !important;
            color: var(--ink2) !important;
            border-radius: 6px !important;
            font-family: var(--mono) !important;
            font-size: 0.78rem !important;
        }
        [data-testid="stSidebar"] .stTextArea textarea:focus {
            border-color: var(--border3) !important;
            box-shadow: var(--glow) !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: var(--bg2) !important;
            border: 1px solid var(--border) !important;
            color: var(--ink2) !important;
            border-radius: 6px !important;
            font-family: var(--mono) !important;
            font-size: 0.78rem !important;
            text-align: left !important;
            transition: all 0.2s !important;
            letter-spacing: 0.02em !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: var(--green-dim) !important;
            border-color: var(--border3) !important;
            color: var(--green) !important;
            box-shadow: var(--glow) !important;
        }
        [data-testid="stSidebar"] label {
            font-family: var(--mono) !important;
            font-size: 0.72rem !important;
            color: var(--muted) !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }

        .masthead {
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.4rem;
            margin-bottom: 2rem;
        }
        .masthead-eyebrow {
            font-family: var(--mono);
            font-size: 0.68rem;
            color: var(--green);
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .masthead-eyebrow::before {
            content: '';
            display: inline-block;
            width: 24px; height: 1px;
            background: var(--green);
        }
        .masthead h1 {
            font-family: var(--serif) !important;
            font-size: clamp(2.2rem, 4vw, 3.4rem) !important;
            font-weight: 400 !important;
            font-style: italic !important;
            color: var(--ink) !important;
            margin: 0 0 0.5rem !important;
            line-height: 1.05 !important;
            letter-spacing: -0.02em !important;
        }
        .masthead h1 em { color: var(--green); font-style: normal; }
        .masthead-sub {
            font-family: var(--mono);
            font-size: 0.78rem;
            color: var(--muted);
            letter-spacing: 0.04em;
            max-width: 60ch;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-family: var(--mono);
            font-size: 0.65rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            padding: 0.2rem 0.7rem;
            border-radius: 2px;
            border: 1px solid;
            margin-left: auto;
        }
        .status-badge.online {
            color: var(--green);
            border-color: var(--border3);
            background: var(--green-dim);
        }
        .status-badge .dot {
            width: 5px; height: 5px;
            border-radius: 50%;
            background: var(--green);
            animation: blink 1.8s ease-in-out infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }

        .input-shell {
            background: var(--bg1);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.4rem 1.6rem 1rem;
            margin-bottom: 1.5rem;
            position: relative;
        }
        .input-shell::before {
            content: 'QUERY_INPUT';
            position: absolute;
            top: -0.55rem; left: 1rem;
            font-family: var(--mono);
            font-size: 0.60rem;
            letter-spacing: 0.12em;
            color: var(--green);
            background: var(--bg1);
            padding: 0 0.5rem;
        }
        .stTextArea textarea {
            background: var(--bg2) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            color: var(--ink) !important;
            font-family: var(--mono) !important;
            font-size: 0.88rem !important;
            line-height: 1.7 !important;
            caret-color: var(--green) !important;
        }
        .stTextArea textarea:focus {
            border-color: var(--border3) !important;
            box-shadow: var(--glow) !important;
        }
        .stTextArea textarea::placeholder { color: var(--muted) !important; font-style: italic; }
        label[data-testid="stWidgetLabel"] {
            font-family: var(--mono) !important;
            font-size: 0.70rem !important;
            color: var(--muted) !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
        }

        [data-testid="stBaseButton-primary"],
        .stButton > button[kind="primary"] {
            background: var(--green2) !important;
            border: none !important;
            color: #0a0d0f !important;
            font-family: var(--mono) !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            border-radius: 4px !important;
            padding: 0.6rem 1.4rem !important;
            transition: all 0.2s !important;
            box-shadow: 0 0 24px rgba(34,197,94,0.25) !important;
        }
        [data-testid="stBaseButton-primary"]:hover,
        .stButton > button[kind="primary"]:hover {
            background: var(--green) !important;
            box-shadow: 0 0 36px rgba(74,222,128,0.4) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stBaseButton-secondary"],
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border: 1px solid var(--border2) !important;
            color: var(--muted) !important;
            font-family: var(--mono) !important;
            font-size: 0.78rem !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            border-radius: 4px !important;
        }
        [data-testid="stBaseButton-secondary"]:hover,
        .stButton > button[kind="secondary"]:hover {
            border-color: var(--border3) !important;
            color: var(--ink2) !important;
        }
        [data-testid="stDownloadButton"] > button,
        .stDownloadButton > button {
            background: var(--bg2) !important;
            border: 1px solid var(--border2) !important;
            color: var(--green) !important;
            font-family: var(--mono) !important;
            font-size: 0.75rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            border-radius: 4px !important;
            transition: all 0.2s !important;
        }
        [data-testid="stDownloadButton"] > button:hover,
        .stDownloadButton > button:hover {
            background: var(--green-dim) !important;
            border-color: var(--border3) !important;
            box-shadow: var(--glow) !important;
        }

        .pipeline-wrap {
            background: var(--bg1);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.4rem 1.6rem 1.2rem;
            margin-bottom: 1.5rem;
            position: relative;
        }
        .pipeline-wrap::before {
            content: 'PIPELINE_STATUS';
            position: absolute;
            top: -0.55rem; left: 1rem;
            font-family: var(--mono);
            font-size: 0.60rem;
            letter-spacing: 0.12em;
            color: var(--green);
            background: var(--bg1);
            padding: 0 0.5rem;
        }
        .pipeline-track {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 0.6rem;
            margin-bottom: 1rem;
        }
        .phase-node {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.4rem;
            padding: 0.9rem 0.5rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--bg2);
            transition: all 0.3s ease;
            position: relative;
        }
        .phase-node.active {
            border-color: var(--green2);
            background: rgba(34,197,94,0.06);
            box-shadow: 0 0 16px rgba(34,197,94,0.12), inset 0 0 12px rgba(34,197,94,0.04);
        }
        .phase-node.done {
            border-color: rgba(74,222,128,0.30);
            background: rgba(74,222,128,0.04);
        }
        .phase-node.done::after {
            content: '\2713';
            position: absolute;
            top: 4px; right: 6px;
            font-size: 0.6rem;
            color: var(--green);
            font-family: var(--mono);
        }
        .phase-num { font-family: var(--mono); font-size: 0.60rem; color: var(--muted); letter-spacing: 0.1em; }
        .phase-node.active .phase-num { color: var(--green); }
        .phase-icon-lg { font-size: 1.4rem; line-height: 1; }
        .phase-label { font-family: var(--mono); font-size: 0.65rem; color: var(--ink2); letter-spacing: 0.05em; text-align: center; }
        .phase-node.active .phase-label { color: var(--green); }
        .phase-bar { height: 2px; border-radius: 1px; background: var(--bg3); overflow: hidden; margin-top: 0.2rem; width: 100%; }
        .phase-node.active .phase-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--green2), var(--green));
            animation: scan 1.4s ease-in-out infinite;
            width: 60%;
        }
        .phase-node.done .phase-bar-fill { height: 100%; background: var(--green2); width: 100%; }
        @keyframes scan { 0% { margin-left: -60%; } 100% { margin-left: 100%; } }
        .pipeline-log {
            font-family: var(--mono);
            font-size: 0.72rem;
            color: var(--muted);
            border-top: 1px solid var(--border);
            padding-top: 0.75rem;
            min-height: 1.4rem;
            letter-spacing: 0.03em;
        }
        .pipeline-log .log-prefix { color: var(--green); margin-right: 0.5rem; }
        .pipeline-log .log-node { color: var(--cyan); }

        .event-log-wrap {
            background: var(--bg1);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.2rem;
            margin-top: 0.8rem;
            font-family: var(--mono);
            font-size: 0.72rem;
            max-height: 180px;
            overflow-y: auto;
            line-height: 1.8;
        }
        .log-line { display: flex; gap: 0.8rem; align-items: baseline; }
        .log-time { color: var(--muted); flex-shrink: 0; width: 5ch; }
        .log-type-start { color: var(--cyan); }
        .log-type-end   { color: var(--green); }
        .log-type-err   { color: var(--red); }
        .log-msg { color: var(--ink2); }

        .report-shell {
            background: var(--bg1);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 2rem 2.2rem 1.6rem;
            margin-bottom: 1.5rem;
            position: relative;
        }
        .report-shell::before {
            content: 'REPORT_OUTPUT';
            position: absolute;
            top: -0.55rem; left: 1rem;
            font-family: var(--mono);
            font-size: 0.60rem;
            letter-spacing: 0.12em;
            color: var(--green);
            background: var(--bg1);
            padding: 0 0.5rem;
        }
        .stMarkdown h1 {
            font-family: var(--serif) !important;
            font-style: italic !important;
            font-weight: 400 !important;
            font-size: 2rem !important;
            color: var(--ink) !important;
            border-bottom: 1px solid var(--border) !important;
            padding-bottom: 0.5rem !important;
            margin-bottom: 1.2rem !important;
        }
        .stMarkdown h2 {
            font-family: var(--sans) !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            color: var(--green) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            margin-top: 1.8rem !important;
            margin-bottom: 0.6rem !important;
        }
        .stMarkdown h3 { font-family: var(--mono) !important; font-size: 0.88rem !important; color: var(--cyan) !important; letter-spacing: 0.05em !important; }
        .stMarkdown p { color: var(--ink2) !important; line-height: 1.8 !important; font-size: 0.95rem !important; }
        .stMarkdown code { font-family: var(--mono) !important; background: var(--bg3) !important; color: var(--green) !important; padding: 0.1em 0.4em !important; border-radius: 3px !important; font-size: 0.85em !important; }
        .stMarkdown blockquote { border-left: 2px solid var(--green2) !important; padding-left: 1rem !important; margin-left: 0 !important; color: var(--ink2) !important; }
        .stMarkdown a { color: var(--cyan) !important; }
        .stMarkdown hr { border-color: var(--border) !important; }
        .stMarkdown table { border-collapse: collapse !important; width: 100% !important; }
        .stMarkdown th { background: var(--bg3) !important; color: var(--green) !important; font-family: var(--mono) !important; font-size: 0.75rem !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; padding: 0.5rem 0.8rem !important; border: 1px solid var(--border) !important; }
        .stMarkdown td { color: var(--ink2) !important; padding: 0.45rem 0.8rem !important; border: 1px solid var(--border) !important; font-size: 0.88rem !important; }

        .archive-shell {
            background: var(--bg1);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.4rem 1.6rem 1rem;
            margin-bottom: 1.5rem;
            position: relative;
        }
        .archive-shell::before {
            content: 'ARCHIVED_REPORT';
            position: absolute;
            top: -0.55rem; left: 1rem;
            font-family: var(--mono);
            font-size: 0.60rem;
            letter-spacing: 0.12em;
            color: var(--amber);
            background: var(--bg1);
            padding: 0 0.5rem;
        }

        .export-label {
            font-family: var(--mono);
            font-size: 0.60rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.5rem;
        }

        .stAlert { background: var(--bg2) !important; border-color: var(--border2) !important; color: var(--ink2) !important; font-family: var(--mono) !important; font-size: 0.82rem !important; border-radius: 6px !important; }
        .stExpander { background: var(--bg1) !important; border: 1px solid var(--border) !important; border-radius: 6px !important; }
        .stExpander summary { font-family: var(--mono) !important; font-size: 0.78rem !important; color: var(--muted) !important; letter-spacing: 0.06em !important; }
        hr { border-color: var(--border) !important; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.45s ease-out; }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg2); }
        ::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--green2); }
        </style>
        """,
        unsafe_allow_html=True,
    )
