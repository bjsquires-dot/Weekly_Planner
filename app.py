import streamlit as st
import pandas as pd
import google.generativeai as genai
genai.configure(api_key='AIzaSyDk9ve8h4yXJDRN7S3uIIZfxLSxKA_19eY', transport='rest')
model = genai.GenerativeModel('gemini-2.5-flash')

def graph_today(df, latest_week):
    categories = ['TT', 'PS', 'HS', 'E', 'WDU']
    chart_data = []

    for col in categories:
        actual_col = f"{col} actual"
        goal_col = f"{col} goal"

        # We check if BOTH columns exist in the file before adding them
        if actual_col in df.columns and goal_col in df.columns:
            actual_val = latest_week[actual_col]
            chart_data.append({
                "Metric": col,
                "Value": float(actual_val) if pd.notnull(actual_val) else 0.0,
                "Type": "Actual ✅"
            })
            goal_val = latest_week[goal_col]
            chart_data.append({
                "Metric": col,
                "Value": float(goal_val) if pd.notnull(goal_val) else 0.0,
                "Type": "Goal 🎯"
            })
        else:
            # This helps you debug which category is missing
            st.warning(f"Note: Could not find columns for {col} in your CSV.")

    if not chart_data:
        st.error("No valid metrics found to chart. Check your CSV headers!")
        return

    # Convert to long-form DataFrame for the bar chart
    plot_df = pd.DataFrame(chart_data)

    # 5. VISUALIZATION
    st.bar_chart(
        plot_df,
        x="Metric",
        y="Value",
        color="Type",
        stack=False
    )

def update_goals(df, latest_week):
    with st.expander("Update Goals"):



        # Create columns for the input boxes
        cols = st.columns(5)
        categories = ['TT', 'PS', 'HS', 'E', 'WDU']
        new_values = {}

        for i, cat in enumerate(categories):
            with cols[i]:
                current_val = latest_week[f"{cat} actual"]
                safe_current = float(current_val) if pd.notnull(current_val) else 0.0
                new_values[f"{cat} actual"] = st.number_input(f"{cat}", value=safe_current, min_value = 0.0, step=1.0)

        if st.button("Save Changes"):
            # Update the last row of the dataframe
            idx = df.index[-1]
            for col_name, val in new_values.items():
                df.at[idx, col_name] = val

            # Save back to CSV
            df.to_csv('weekly planning - data.csv', index=False)
            st.success("Data updated! Refreshing...")
            st.rerun()  # This force-refreshes the app to update the graph



def make_today_screen(df):
    df.columns = df.columns.str.strip()

    # Cleaning rows (removes rows where the date is missing)
    df = df.dropna(subset=['weekly ending'])
    st.title("🎯 Goals Dashboard")
    # Grabbing the last entry
    latest_week = df.iloc[-1]
    st.subheader(f"Review for the week: {latest_week['weekly ending']}")
    # Plots graph
    graph_today(df, latest_week)
    update_goals(df, latest_week)


def make_history_screen(df):
    st.title("📈 Progress History")
    select = st.selectbox("Goals", ['TT', 'PS', 'HS', 'E', 'WDU'])
    actual_col = f"{select} actual"
    goal_col = f"{select} goal"
    new_df = df[['weekly ending', actual_col, goal_col]]
    new_df['weekly ending'] = pd.to_datetime(new_df['weekly ending'])
    new_df = new_df.set_index('weekly ending')
    new_df = new_df.sort_index()
    st.line_chart(new_df)


# @st.cache_data
# def load_data(file_path):
#     df = pd.read_csv(file_path)
#     return df


def ask_chat(df, prompt, sys_inst):
    full_prompt = f"{sys_inst}\n\nData:\n{df.to_csv(index=False)}\n\nQuestion: {prompt}"
    response = model.generate_content(full_prompt)

    # Display it in the chat bubble
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
    st.session_state.messages.append({"role": "assistant", "content": response.text, "avatar": "🤖"})

def make_ai_screen(df):
    system_instruction = """
    You are a Read-Only Goal Coach. 
    You have access to the user's data below, but you cannot change it. 
    Your job is to:
    1. Identify trends 
    2. Be concise, actionable and focused
    3.Use bullet points for readability.
    4. Do NOT use code blocks (```) for your plain text responses; use standard markdown.
    For reference TT = Temple Trips PS, = Personal Scripture Study, HS = Hours studied, WDU = Weekly Device Usage, E = Exercises
    """
    data_files = ['weekly planning - data.csv']

    st.title("🤖 AI Goal Coach")

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])


    st.subheader('Suggested Questions')
    col1, col2, col3 = st.columns(3)
    preset_prompt = None
    with col1:
        if st.button("📈 Spot Trends"):
            preset_prompt = "Analyze my goal history and tell me one positive trend you see."
            st.session_state.messages.append({"role": "user", "content": preset_prompt, "avatar": "👤"})
            ask_chat(df, preset_prompt, system_instruction)
    with col2:
        if st.button("⚠️ Risk Check"):
            preset_prompt = "Which goal am I most likely to miss this week based on past data?"
            st.session_state.messages.append({"role": "user", "content": preset_prompt, "avatar": "👤"})
            ask_chat(df, preset_prompt, system_instruction)
    with col3:
        if st.button("💡 Get Advice"):
            preset_prompt = "Give me 3 actionable tips to improve my WDU score."
            st.session_state.messages.append({"role": "user", "content": preset_prompt, "avatar": "👤"})
            ask_chat(df, preset_prompt, system_instruction)

    st.divider()

    chat_layout = st.container()
    with chat_layout:
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=message.get("avatar")):
                st.markdown(message["content"])

    if prompt:= st.chat_input("Talk to me!"):
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": "👤" })
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        ask_chat(df, st.session_state.messages[-1]["content"], system_instruction)

def make_relation_page(df):
    pass

def main():
    st.set_page_config(page_title="Weekly Planner", layout="wide")
    df = pd.read_csv('weekly planning - data.csv')
    st.sidebar.title("Navigation")
    st.divider()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    page = st.sidebar.radio("Go to", ["Weekly Entry", "Past Data", "AI Assistant", "Relationships"])
    if page == "Weekly Entry":
        make_today_screen(df)
    elif page == "Past Data":
        make_history_screen(df)
    elif page == "AI Assistant":
        make_ai_screen(df)
    elif page == "Relationships":
        make_relation_page(df)




if __name__ == "__main__":
    main()