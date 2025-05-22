from flask import Flask, request, render_template, send_file, redirect, url_for
import csv
import mysql.connector
from datetime import datetime
import os
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'data'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
csv.field_size_limit(30000000)  # Increase field size limit

# Database connection function
def db_conn():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='testing_pages'
    )

# Type conversion helpers
def to_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def to_nullable_int(value):
    try:
        return int(value) if value not in ('', None, 'NULL', 'null') else None
    except (ValueError, TypeError):
        return None

def to_nullable_str(value):
    if value is None:
        return None
    val = value.strip()
    return val if val.lower() != 'null' and val != '' else None

def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

# Upload route
@app.route('/', methods=['GET', 'POST'])
def upload_csv():
    message = None
    if request.method == 'POST':
        file = request.files.get('file')
        table = request.form.get('table')

        if not file or not file.filename.endswith('.csv'):
            message = "❌ Please upload a valid CSV file."
            return render_template('upload.html', message=message)

        if table not in ('posts', 'pages'):
            message = "❌ Please select a valid table."
            return render_template('upload.html', message=message)

        path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(path)

        try:
            conn = db_conn()
            cursor = conn.cursor()
            batch = []
            batch_size = 5000

            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if table == 'posts':
                        created_at = parse_datetime(row.get('created_at'))
                        updated_at = parse_datetime(row.get('updated_at'))
                        original_post_type = to_nullable_str(row.get('post_type'))
                        post_type = 'article' if original_post_type in (None, '', 'null', 'post') else original_post_type

                        batch.append((
                            to_nullable_int(row.get('lang_id')),
                            to_nullable_str(row.get('title')),
                            to_nullable_str(row.get('slug') or row.get('title', '').replace(' ', '-').lower()),
                            to_nullable_str(row.get('title_hash')),
                            to_nullable_str(row.get('keywords')),
                            to_nullable_str(row.get('summary')),
                            to_nullable_str(row.get('content')),
                            to_nullable_str(row.get('optional_url')),
                            to_nullable_int(row.get('pageviews')),
                            to_nullable_int(row.get('comment_count')),
                            to_nullable_int(row.get('need_auth')),
                            to_nullable_int(row.get('slider_order')),
                            to_nullable_int(row.get('featured_order')),
                            to_nullable_int(row.get('is_scheduled')),
                            to_nullable_int(row.get('visibility')),
                            to_nullable_int(row.get('show_right_column')),
                            post_type,
                            to_nullable_str(row.get('video_path')),
                            to_nullable_str(row.get('video_storage')),
                            to_nullable_str(row.get('image_url')),
                            to_nullable_str(row.get('video_url')),
                            to_nullable_str(row.get('video_embed_code')),
                            to_nullable_int(row.get('status')),
                            to_nullable_int(row.get('feed_id')),
                            to_nullable_str(row.get('post_url')),
                            to_nullable_int(row.get('show_post_url')),
                            to_nullable_str(row.get('image_description')),
                            to_nullable_int(row.get('show_item_numbers')),
                            to_nullable_int(row.get('is_poll_public')),
                            to_nullable_str(row.get('link_list_style')),
                            to_nullable_str(row.get('recipe_info')),
                            to_nullable_str(row.get('post_data')),
                            to_nullable_int(row.get('category_id')),
                            to_nullable_int(row.get('user_id')),
                            created_at if created_at else datetime.now(),
                            updated_at if updated_at else datetime.now()
                        ))
                    elif table == 'pages':
                        created_at = parse_datetime(row.get('created_at'))
                        batch.append((
                            to_nullable_int(row.get('lang_id')),
                            to_nullable_str(row.get('title')),
                            to_nullable_str(row.get('slug')),
                            to_nullable_str(row.get('description')),
                            to_nullable_str(row.get('keywords')),
                            to_nullable_int(row.get('is_custom')),
                            to_nullable_str(row.get('page_default_name')),
                            to_nullable_str(row.get('page_content')),
                            to_nullable_int(row.get('page_order')),
                            to_nullable_int(row.get('visibility')),
                            to_nullable_int(row.get('title_active')),
                            to_nullable_int(row.get('breadcrumb_active')),
                            to_nullable_int(row.get('right_column_active')),
                            to_nullable_int(row.get('need_auth')),
                            to_nullable_str(row.get('location')),
                            to_nullable_str(row.get('link')),
                            to_nullable_int(row.get('parent_id')),
                            to_nullable_str(row.get('page_type')),
                            created_at if created_at else datetime.now()
                        ))

                    if len(batch) >= batch_size:
                        cursor.executemany(INSERT_QUERIES[table], batch)
                        conn.commit()
                        batch.clear()

                if batch:
                    cursor.executemany(INSERT_QUERIES[table], batch)
                    conn.commit()

            cursor.close()
            conn.close()
            message = f"✅ CSV imported successfully into '{table}' table!"

        except Exception as e:
            message = f"❌ Import failed: {str(e)}"

    return render_template('upload.html', message=message)

# Download pages SQL
@app.route('/download-pages-sql')
def download_pages_sql():
    try:
        conn = db_conn()
        cursor = conn.cursor()

        cursor.execute("SHOW CREATE TABLE pages")
        create_stmt = cursor.fetchone()[1]

        cursor.execute("SELECT * FROM pages")
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]

        insert_statements = []
        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append("NULL")
                elif isinstance(val, str):
                    values.append("'" + val.replace("'", "''") + "'")
                else:
                    values.append(str(val))
            insert_statements.append(
                f"INSERT INTO pages (`{'`, `'.join(cols)}`) VALUES ({', '.join(values)});"
            )

        dump = "-- SQL Dump of pages table\n\n"
        dump += "SET SQL_MODE = \"NO_AUTO_VALUE_ON_ZERO\";\n"
        dump += "START TRANSACTION;\n\n"
        dump += create_stmt + ";\n\n"
        dump += "\n".join(insert_statements)
        dump += "\n\nCOMMIT;\n"

        buffer = io.BytesIO()
        buffer.write(dump.encode())
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="pages.sql", mimetype="application/sql")

    except Exception as e:
        return f"❌ Failed to generate SQL dump: {str(e)}"

# Delete pages
@app.route('/delete-pages')
def delete_pages():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE pages")
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('upload_csv'))
    except Exception as e:
        return f"❌ Failed to delete pages: {str(e)}"

# Insert queries
INSERT_QUERIES = {
    'posts': """
        INSERT INTO posts (
            lang_id, title, slug, title_hash, keywords, summary, content,
            optional_url, pageviews, comment_count, need_auth, slider_order,
            featured_order, is_scheduled, visibility, show_right_column,
            post_type, video_path, video_storage, image_url, video_url,
            video_embed_code, status, feed_id, post_url, show_post_url,
            image_description, show_item_numbers, is_poll_public,
            link_list_style, recipe_info, post_data, category_id, user_id,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s
        )
    """,
    'pages': """
        INSERT INTO pages (
            lang_id, title, slug, description, keywords,
            is_custom, page_default_name, page_content, page_order, visibility,
            title_active, breadcrumb_active, right_column_active, need_auth,
            location, link, parent_id, page_type, created_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
    """
}

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)