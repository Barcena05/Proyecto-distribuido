from utils import find_duplicate_files
from sklearn.feature_extraction.text import TfidfVectorizer
from flask import Flask, send_file, request
from io import BytesIO
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

@app.route('/preprocess')
def preprocess():
    hashes = find_duplicate_files("data")
    vectorizer = TfidfVectorizer(lowercase=True,strip_accents='unicode')
    indexs = {}
    texts = []
    count = 0
    for hash_value, filevalues in hashes.items():
        for filevalue in filevalues:
            indexs[count] = (filevalue[0], filevalue[1], hash_value)
            count += 1
            texts.append(filevalue[0])

    X = vectorizer.fit_transform(texts)
    app.config['hashes'] = hashes
    app.config['X'] = X
    app.config['indexs'] = indexs
    app.config['vectorizer'] = vectorizer
    return 'Preprocess completed', 200

@app.route('/query/<query>/<file_format>')
def query_func(query:str, file_format:str):
    hashes = app.config['hashes']
    X = app.config['X']
    indexs = app.config['indexs']
    vectorizer = app.config['vectorizer']
    query_vector = vectorizer.transform([query])

    result = cosine_similarity(X, query_vector).flatten()

    indices = result.argsort()[::-1]

    visited_hashes = set()
    outputs = []
    for idx in indices:
        if result[idx] < 0: continue
        filename, fileformat, hash_value = indexs[idx]
        if hash_value not in visited_hashes:
            visited_hashes.add(hash_value)
            for filename, fileformat in hashes[hash_value]:
                if file_format == 'Any' or fileformat == file_format:
                    print(filename)
                    outputs.append((filename, fileformat))
                    break

    return outputs


@app.route('/download/<filename>/<fileformat>')
def download(filename, fileformat):  
    with open(f'data/{filename}.{fileformat}', 'rb') as file:
        file_content = file.read()
        return send_file(
            BytesIO(file_content),
            mimetype='application/octet-stream',
            download_name=filename,
            as_attachment=True
        )


@app.route('/upload/<filename>', methods=['POST'])
def upload(filename):
    print(filename)
    if filename not in request.files:
        return 'No file part', 400
    file = request.files[filename]
    if file.filename == '':
        return 'No selected file', 400
    if file:
        file.save(f'data/{filename}')
        return 'File uploaded successfully', 200
     
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)