# starling-capture-api

## Dev setup

This project uses `pipenv` to manage dependencies and the Python environment (this is like `npm` or `bundler`, but for Python). To install `pipenv` on Mac:
```bash
brew install pipenv
```

See https://github.com/pypa/pipenv#installation for installation instructions in other systems.

Install all Python dependencies:
 ```
 pipenv install
 ```

To get a shell within the Python environment for this project:
```
pipenv shell
```
This will log you into the virtualenv that pipenv has created for this environment.

See https://pipenv.pypa.io/en/latest/ for more detailed `pipenv` documentation.

To run the server:
```
pipenv run server
```

## Configuration via env variables

You can use a local `.env` file in development for setting environment variables. See `.env.example` for available variables, and `config.py` for the place where the variables are loaded.

## Creating and sending JWTs in development

You can create a JWT on https://jwt.io/. Make sure to use the same secret you are using in your development server (the value of `JWT_SECRET`). The algorithm should be `HS256`.

To send a request with a JWT to a server using curl:

```
curl -H "Authorization: Bearer <JWT GOES HERE>" http://localhost:8080/<your_endpoint>
```
