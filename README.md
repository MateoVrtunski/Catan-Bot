# CATAN HELPER

This project is a Catan bot that works like a helper for the game settlers of catan.
You can play the game against him or with his help. You input the games actions and when clicking the decision button(s) you get the helpers decision that you input into the game.
The game is set to 3 player and can be easily set for 4 players but for testing purposes it was faster to play 3 player games.

It is assumed that you know how to play the game regarding rules.

## Power up the project

To start the project run the game.py file and click on the * Running on http://127.0.0.1:5000 link.

1.) Input the board that you like or the board that is in front of you if playing against friends or on online catan.

2.) Choose the order of the players as well as name nad color.

3.) Use the decision button and your player id (first player -> 0, second -> 1 and third -> 3) to get the decision where to place your starting settlments. 
The decision/strategy is based on the board and how "rare" the resources are. It then poers up linear programs for each startegy and picks the best.

4.) When everybody placed their 2 settlements, start the game.

## User Interface (important)
First you see all the players info as well as the "current player".
How a complete turn looks like: Input the number that the dice gave you in the real game. It will automatically give ressources to everybody.

1.) If it is another players turn just input his actions in the Helper, use the decision button only if a trade is asked and trade if Helper decision says so. Then pass the turn.
2.) If it is your turn first, if the dice was 7, click on the "Robber" button to get the decision where to put the robber. 
Then if you have special cards (knight, monopoly, years of plenty, or two-roads) click the button "Card". After that click on the decison button and do as the helper says. 
These buttons can also be played in different order. For trades, buying cards and robbing use the editor to match your ressources and cards in the real game. 

Lastly: When the decision asks for a trade first ask for a 1:1 trade with real players if not trade with the bank accordingly to your harbours or if you don't have them 4:1.

Enjoy the game! 

## Disclaimer
Testing was made on the offficial Catan online game against bots which have 3 difficulties ("rookie", "veteran" and "master").
Helper can beat the "rookie" bots with ease on catan online and even "veterans". Playing against masters is a possible win but Catan also involves a good portion of luck so it is not possible to win every time. 
