# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import json
import csv
from datetime import datetime
import os
import pandas as pd
from collections import defaultdict
import random 

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change this to a secure secret key

# Load questions from JSON file
def load_questions():
    with open('questions.json', 'r') as file:
        data = json.load(file)
        questions = data['questions']  # Access the 'questions' list from the JSON
        random.shuffle(questions)  # Randomize the questions
        return questions

# Store the randomized questions in a global variable
questions = load_questions()

# Log user answers to CSV
def log_answer(question_data, user_answer, is_correct):
    filename = 'user_answers.csv'
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                'Date', 
                'Subject', 
                'Syllabus Topic', 
                'Question', 
                'User Answer', 
                'Correct?'
            ])
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            question_data['subject'],
            question_data['syllabus_topic'],
            question_data['question'],
            user_answer,
            is_correct
        ])

@app.route('/')
def index():
    try:
        #questions = load_questions()
        if 'current_question' not in session:
            session['current_question'] = 0
        
        if session['current_question'] >= len(questions):
            return redirect(url_for('completed'))
        
        question = questions[session['current_question']]
        return render_template('question.html', 
                             question=question,
                             question_number=session['current_question'] + 1,
                             total_questions=len(questions))
    except Exception as e:
        return f"Error loading questions: {str(e)}"

@app.route('/submit', methods=['POST'])
def submit():
    try:
        #questions = load_questions()
        current_question = questions[session['current_question']]
        user_answer = request.form.get('answer')
        
        is_correct = user_answer == current_question['correct_answer']
        
        # Pass the entire question data to log_answer
        log_answer(current_question, user_answer, is_correct)
        
        return render_template('result.html',
                             question=current_question,
                             user_answer=user_answer,
                             is_correct=is_correct,
                             explanation=current_question['explanation'],
                             subject=current_question['subject'],
                             syllabus_topic=current_question['syllabus_topic'])
    except Exception as e:
        return f"Error processing answer: {str(e)}"

@app.route('/next')
def next_question():
    session['current_question'] = session.get('current_question', 0) + 1
    return redirect(url_for('index'))

@app.route('/completed')
def completed():
    session.clear()
    return render_template('completed.html')

@app.route('/dashboard')
def dashboard():
    # Read the CSV file
    df = pd.read_csv('user_answers.csv')

    # Convert the 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Extract just the date part (without time)
    df['Date'] = df['Date'].dt.date
    
    # Convert to string for JSON serialization
    df['Date'] = df['Date'].astype(str)
    
    # Group by date and count correct/incorrect answers
    daily_results = df.groupby(['Date', 'Correct?']).size().unstack(fill_value=0)

    # Prepare data for the bar chart
    dates = daily_results.index.tolist()
    correct_counts = daily_results[True].tolist() if True in daily_results.columns else [0] * len(dates)
    incorrect_counts = daily_results[False].tolist() if False in daily_results.columns else [0] * len(dates)

    # Debug print statements
    print("Daily Results:")
    print(daily_results)
    print("Dates:", dates)
    print("Correct Counts:", correct_counts)
    print("Incorrect Counts:", incorrect_counts)

    # Calculate percentage correct by subject per day
    subject_results = df.groupby(['Date', 'Subject', 'Correct?']).size().unstack(fill_value=0)
    print("Subject Results:")
    print(subject_results)

    # Calculate percentage correct by subject per day
    subject_percentage = df.pivot_table(index='Date', columns='Subject', values='Correct?', aggfunc=lambda x: (x[x==True].count() / len(x)) * 100)
    subject_percentage = subject_percentage.fillna(0)  # replace NaN with 0
    print("Subject Percentage:")
    print(subject_percentage)

    # Fix the structure of subject_percentage DataFrame
    subject_percentage = subject_percentage.reset_index(level=0, drop=True)
    print("Fixed Subject Percentage:")
    print(subject_percentage)

    subjects = subject_percentage.columns.tolist()
    subject_data = {subject: subject_percentage[subject].tolist() for subject in subjects}

    # Debug print statements
    print("Subjects:", subjects)
    print("Subject Data:", subject_data)

    # Create a pivot table with the subjects as columns and the dates as rows
    subject_table_df = df.pivot_table(index='Date', columns='Subject', values='Correct?', aggfunc=lambda x: (x[x==True].count() / len(x)) * 100)
    # Transpose the subject_percentage DataFrame
    subject_table_df = subject_table_df.transpose()
    # Create an HTML table from the pivot table DataFrame
    subject_table = subject_table_df.to_html(float_format=lambda x: '{:.0f}%'.format(x))

    # print("------------------------------------")
    # # Set display options to show all columns and full width
    # pd.set_option('display.max_columns', None)  # Show all columns
    # pd.set_option('display.expand_frame_repr', False)  # Do not wrap DataFrame in the output
    # print(df)
    # print("------------------------------------")
    
    # Create a pivot table for syllabus_topic
    syllabus_topic_table_df = df.pivot_table(index='Date', columns='Syllabus Topic', values='Correct?', aggfunc=lambda x: (x[x==True].count() / len(x)) * 100)
    syllabus_topic_table_df = syllabus_topic_table_df.transpose()
    # Create an HTML table from the pivot table DataFrame
    syllabus_topic_table = syllabus_topic_table_df.to_html(float_format=lambda x: '{:.0f}%'.format(x))

    return render_template('dashboard.html', 
                            dates=dates,
                            correct_counts=correct_counts,
                            incorrect_counts=incorrect_counts,
                            subjects=subjects,
                            subject_data=subject_data,
                            subject_table=subject_table,
                            syllabus_topic_table=syllabus_topic_table)


    
if __name__ == '__main__':
    app.run(debug=True)