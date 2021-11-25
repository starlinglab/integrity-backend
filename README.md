# starling-capture-api <!-- omit in toc -->

- [Dev setup](#dev-setup)
- [Configuration](#configuration)
- [Creating and sending JWTs in development](#creating-and-sending-jwts-in-development)
- [Dockerized Debian development environment](#dockerized-debian-development-environment)

## Dev setup

This is a Python3 project.  This project uses `pipenv` to manage dependencies and the Python environment (this is like `npm` or `bundler`, but for Python). To install `pipenv` on Mac:
```bash
brew install pipenv
```

See https://github.com/pypa/pipenv#installation for installation instructions in other systems.

The [Pipfile](./Pipfile) list all our dependencies. To install them:
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

## Configuration

The server is configured entirely via environment variables. See [config.py](./starling-capture-api/config.py) for the available variables and some notes about each. In development, you can use a local `.env` file setting environment variables. See `.env.example` for an example.

Most importantly, you will need to provide:
* `CLAIM_TOOL_PATH`: A path to a fully working `claim_tool` binary. The server should have permissions to execute it, and it should be correctly configured with its keys.
* `IMAGES_DIR`: A path to a directory to store images. The server will need write access to this directory. This will be the persistent storage for the received images with their attestations.

## Creating and sending JWTs in development

You can create a JWT on https://jwt.io/. Make sure to use the same secret you are using in your development server (the value of `JWT_SECRET`). The algorithm should be `HS256`.

To send a request with a JWT to a server using curl:

```
curl -X POST  http://localhost:8080/assets/create -H "Authorization: Bearer <JWT>" \
     -H "Content-Type: multipart/form-data" -F "file=@<image_filename>>"
```

## Dockerized Debian development environment

To run the `claim-tool` version in a Debian environment (as it will be in production), use the provided `docker-compose.yml` (and `Dockerfile`).

To get a shell inside the container:
```
docker-compose run --service-ports api bash
```

Once inside the container, run the usual commands (`pipenv install`, etc). You will also need a `claim_tool` binary inside your container (you can use `docker cp` to copy it into the container), as well as a directory for image storage.
