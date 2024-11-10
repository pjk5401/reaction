from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from config import Config
import random

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key'

WORDS = {
    1: {"correct_word": "고양이", "incorrect_word": "곡양이"},
    2: {"correct_word": "토끼", "incorrect_word": "도끼"},
    3: {"correct_word": "강아지", "incorrect_word": "겅어지"},
    4: {"correct_word": "기린", "incorrect_word": "기딘"},
    5: {"correct_word": "코끼리", "incorrect_word": "코기리"}
}

# MySQL 연결 설정
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

def get_statistics(gender=None, age_group=None, game=None, rank=None):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    conditions = []
    params = []

    if gender:
        conditions.append("u.gender = %s")
        params.append(gender)
    if age_group:
        conditions.append("u.age_group = %s")
        params.append(age_group)
    if game:
        conditions.append("u.game = %s")
        params.append(game)
    if rank:
        conditions.append("u.rank = %s")
        params.append(rank)

    where_clause = " AND ".join(conditions)
    where_clause = f"WHERE {where_clause}" if where_clause else ""

    query = f"""
        SELECT 
            t.stage,
            AVG(t.reaction_time) AS average_reaction_time,
            SUM(t.success) / COUNT(*) * 100 AS success_rate
        FROM test_records AS t
        JOIN users AS u ON t.user_id = u.id
        {where_clause}
        GROUP BY t.stage
        ORDER BY t.stage
    """
    cur.execute(query, tuple(params))
    statistics = cur.fetchall()
    cur.close()
    conn.close()
    return statistics

def get_rank_statistics(game):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    query = """
        SELECT u.rank, AVG(t.reaction_time) AS average_reaction_time
        FROM test_records AS t
        JOIN users AS u ON t.user_id = u.id
        WHERE u.game = %s AND t.success = TRUE
        GROUP BY u.rank
        ORDER BY FIELD(u.rank, 'iron', 'bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'grandmaster', 'challenger')
    """
    cur.execute(query, (game,))
    rank_statistics = cur.fetchall()
    cur.close()
    conn.close()
    return rank_statistics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test/<int:stage>', methods=['GET', 'POST'])
def test_stage(stage):
    if request.method == 'POST':
        reaction_time = float(request.form.get('reaction_time', 0))
        success = request.form.get('success') == 'true'

        if stage == 1 and 'reaction_time' not in request.form:
            gender = request.form.get('gender')
            age_group = request.form.get('age')
            game = request.form.get('game') or None
            rank = request.form.get('rank') or None
            
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (gender, age_group, game, `rank`) VALUES (%s, %s, %s, %s)",
                        (gender, age_group, game, rank))
            conn.commit()
            session['user_id'] = cur.lastrowid
            cur.close()
            conn.close()
            return redirect(url_for('test_stage', stage=1))

        user_id = session.get('user_id')
        if user_id:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO test_records (user_id, stage, reaction_time, success) VALUES (%s, %s, %s, %s)",
                        (user_id, stage, reaction_time, success))
            conn.commit()
            cur.close()
            conn.close()

        return redirect(url_for('test_stage', stage=stage + 1)) if stage < 5 else redirect(url_for('result'))

    # 단계별 카드 개수 설정
    grid_sizes = {1: 4, 2: 9, 3: 16, 4: 25, 5: 36}
    num_cards = grid_sizes.get(stage, 4)

    # WORDS에서 현재 단계의 단어 가져오기
    words = WORDS.get(stage, {"correct_word": "", "incorrect_word": ""})
    cards = [words["correct_word"]] * (num_cards - 1) + [words["incorrect_word"]]
    random.shuffle(cards)

    return render_template('test_stage.html', stage=stage, cards=cards, incorrect_word=words["incorrect_word"])

@app.route('/result')
def result():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT stage, AVG(reaction_time) 
            FROM test_records 
            WHERE success = TRUE 
            GROUP BY stage 
            ORDER BY stage
        """)
        overall_average_times = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT stage, reaction_time, success FROM test_records WHERE user_id = %s ORDER BY stage", (user_id,))
        results = cur.fetchall()

        cur.close()
        conn.close()
        
        return render_template('result.html', results=results, overall_average_times=overall_average_times)
    
    return redirect(url_for('index'))

@app.route('/statistics')
def statistics():
    gender = request.args.get('gender')
    age_group = request.args.get('age_group')
    game = request.args.get('game')
    rank = request.args.get('rank')

    statistics_data = get_statistics(gender=gender, age_group=age_group, game=game, rank=rank)
    rank_statistics = get_rank_statistics(game) if game else []

    return render_template('statistics.html', statistics_data=statistics_data, rank_statistics=rank_statistics)

@app.route('/rank_chart_data')
def rank_chart_data():
    game = request.args.get('game')
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    query = """
        SELECT u.rank, AVG(t.reaction_time) AS average_reaction_time
        FROM test_records t
        JOIN users u ON t.user_id = u.id
        WHERE u.game = %s
        GROUP BY u.rank
        ORDER BY FIELD(u.rank, 'iron', 'bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'grandmaster', 'challenger')
    """
    cur.execute(query, (game,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=15002)
