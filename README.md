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

```
pip install uvicorn[standard]
uvicorn main:app --reload
```
