# VibrantSeas Project Development

## Setup
This project is setup as a Docker Dev Container. I'd recommend reading about both [Docker](https://en.wikipedia.org/wiki/Docker_(software)) and the [VSCode Remote Containers Extension](https://code.visualstudio.com/docs/devcontainers/containers) to get a basic understanding of containerization and how this whole project setup works at a high level. Feel free to look at `.devcontainer/devcontainer.json` and `devcontainer/Dockerfile` to see how this was set up.

First, make sure you have both [Git](https://git-scm.com/) and [Visual Studio Code](https://code.visualstudio.com/) installed (VSCode equivalents like Cursor and Windsurf work as well) along with the previously mentioned devcontainers/remote containers extension installed.

Clone this git repository using the instructions provided by github when you press the `Clone` button and open the folder in VSCode. You should be prompted with a notification to `Reopen in Dev Container`, if you don't see it open the command pallete with `Cmd + Shift + P` or equivalent w/ `Ctrl` and type `Reopen in Container`.

When you first build it, it will take a while to open up. You can see what step of the setup process it is on by pressing `Show Log` in the notification that comes up once the container starts opening. 

Once the container is fully booted up, you can create a new terminal using either the + button on the top right of the terminal window or by opening the command pallete and writing `Create new Terminal`. 

Now your devcontainer is fully set up and you are effectively coding inside of an emulated Linux box with two versions of SeaDAS fully installed!