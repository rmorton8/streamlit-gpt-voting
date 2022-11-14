# Snowpark
import snowflake.connector
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import string
from model import GeneralModel


covid_dict = {
    "test positive, but don't have COVID": 'test positive',
    "test negative, but do have COVID": 'test negative'
}

bank_dict = {
    "bank places hold on credit card, but no fraud occurred": 'credit hold',
    "bank doesn't place a hold, but there was fraud!": 'no-hold, but fraud!'
}

school_dict = {
    "Rejection letter, but it's a mistake and you were actually admitted!": 'false rejection',
    "Acceptance letter, but you were actually mean to be rejected!": 'false acceptance'
}


def insert_row_into_snowflake(vote_choice, table_name):
    my_cnx = snowflake.connector.connect(**st.secrets['snowflake'])
    with my_cnx.cursor() as my_cur:
        my_cur.execute(f"insert into {table_name} values ('{vote_choice}')")
    my_cnx.close()
    return


def grab_data_from_snowflake(table_name):
    my_cnx = snowflake.connector.connect(**st.secrets['snowflake'])
    with my_cnx.cursor() as my_cur:
        my_cur.execute(f"select * from {table_name}")
        output = pd.DataFrame(my_cur.fetchall())
    my_cnx.close()
    return output


def grab_and_plot_data(table_name, values):
    votes = grab_data_from_snowflake(table_name)
    if len(votes) >= 2:
        # transform votes
        counts = votes.value_counts()
        data_dict = {'choice': values, 'count': [counts[values[0]], counts[values[1]]]}
        final_df = pd.DataFrame(data_dict)
        # plot
        fig = px.pie(final_df, values='count', names='choice', title='Voting Results')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write('waiting for votes')
    return


def generate_question_column(table_name, data_dict, question, num):
    col1, col2 = st.columns(2)
    with st.container():
        with col1:
            st.subheader(question)
            output = st.radio("Which is less desirable?",
                                  tuple(data_dict.keys()))
            if not st.button('Vote', key=num):
                st.write('please vote')
            else:
                st.write(f'thanks for voting!')
                insert_row_into_snowflake(data_dict[output], table_name)

        with col2:
            grab_and_plot_data(table_name, values=list(data_dict.values()))
    return


def insert_new_words(words_list):
    my_cnx = snowflake.connector.connect(**st.secrets['snowflake'])
    with my_cnx.cursor() as my_cur:
        for word in words_list:
            my_cur.execute(f"insert into gpt_words values ('{word}')")
    my_cnx.close()
    return


def word_counter(new_words_list):
    insert_new_words(new_words_list)
    # grab all words and plot frequency
    my_cnx = snowflake.connector.connect(**st.secrets['snowflake'])
    with my_cnx.cursor() as my_cur:
        my_cur.execute(f"select * from gpt_words")
        output = pd.DataFrame(my_cur.fetchall())
    my_cnx.close()
    return output
    


def app():

    # Creating an object of prediction service
    pred = GeneralModel()

    api_key = st.sidebar.text_input("APIkey", type="password")
    
    # Add header and a subheader
    st.title('Streamlit Voting Demo')
    st.subheader(
        "Powered by Snowpark for Python and GPT-3 | Made with Streamlit")
    st.header("Vote for the situations you think are less desirable!")

    tab1, tab2, tab3, tab4 = st.tabs(['COVID', 'BANK', 'SCHOOL', "'Roll the dice!"])
    # COVID section
    with tab1:
        question = 'Bob thinks he may have contracted COVID-19, and goes to get tested.'
        generate_question_column("COVID_VOTES", covid_dict, question, 1)

    # Bank section
    with tab2:
        question = 'ABC Bank monitors credit card usage to detect any fraudulent activity.'
        generate_question_column("BANK_VOTES", bank_dict, question, 2)

    # SCHOOL section
    with tab3:
        question = "It's your senior year of highschool and you recieve an admissions letter from your dream school."
        generate_question_column("SCHOOL_VOTES", school_dict, question, 3)
        
    # GPT-3 Section
    with tab4:
        # Using the streamlit cache
        @st.cache
        def process_prompt(input):

            return pred.model_prediction(input=input.strip() , api_key=api_key)

        if api_key:

            # Setting up the Title
            st.title("Write a poem based on these words")

            # st.write("---")

            s_example = "Birds, flowers, love, sun"
            input = st.text_area(
                "Use the example below or input your own text in English",
                value=s_example,
                max_chars=150,
                height=100,
            )

            if st.button("Submit"):
                with st.spinner(text="In progress"):
                    report_text = process_prompt(input)
                    st.markdown(report_text)
                    word_list = re.sub('['+string.punctuation+']', '', report_text.lower()).split()
                    # remove specified words
                    spec_words = re.sub('['+string.punctuation+']', '', input.lower()).split()
                    for word in spec_words:
                        word_list.pop(word)
                    output = word_counter(word_list)
                    st.dataframe(output)
               
        else:
            st.error("🔑 Please enter API Key")
