# fpcrawl
## How to use
    # connect to the instance
        ssh root@crawl
    # attach to a tmux session
        tmux a -t zyx
    # (alternatively create a new one)
        tmux new -t zyx
    # change directory to the dockerfiles
        cd fpcrawl/dockerfiles 
    # (update data)
        (git pull)
    # rebuild docker images 
        docker-compose build
    # start hub
        docker-compose up hub
    # start 14 chrome nodes and the error_restart server
        docker-compose up scale chrome=14 && python3 cr_server.py
    # start fpmon http server
        docker-compose up fpmon
    # start fpmon crawler
        docker-compose up fpcrawl
   
    (other useful commands)
    # delete all docker containers and images
        docker system prune 
   

