deploy:
	git add bot.py Procfile posts.json requirements.txt LICENSE
	git commit -m "Update files" -a
	git push heroku master