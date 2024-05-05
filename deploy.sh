#!/bin/bash
echo "Pushing to GitHub..."
git push origin main
echo "Pushing to Heroku..."
git push heroku main
