# google-photo-backup

## start continer

### simply

```
docker-compose up
docker-compose run python_dev /bin/bash
```

### when connecting to a started container

```
docker exec -it "$(docker ps -qf "name=python_dev")" /bin/bash
```

## stop continer

- simply

```
docker-compose down
```

- when you want to completely erase the image

```
docker-compose down --rmi all
```
