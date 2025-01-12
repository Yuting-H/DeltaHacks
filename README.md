# DeltaHacks

## Running the app

### Running the frontend

```
cd ./client

npm install

npm run dev

```

### Running the server

```
cd ./server
pip install requirements.txt
python -m venv venv
venv\Scripts\activate
```

Install a web server, I use uvicorn,

for windows:

```
pip install uvicorn[standard]
venv\Scripts\activate
uvicorn main:app --reload
```
