# GuessWithEmojiBot 🎬🎭

The ultimate Telegram bot for emoji-based movie guessing games! Built to handle 1000+ groups simultaneously with zero downtime.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue.svg)](https://core.telegram.org/bots/api)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Features

### 🎮 Core Game Features
- **500+ Movie Puzzles** - Hollywood, Bollywood & Tollywood
- **Multiple Difficulty Levels** - Easy, Medium, Hard with different point multipliers
- **Smart Hint System** - Contextual clues to help players
- **Anti-Repetition Logic** - Rotates through 500+ puzzles before repeating
- **Real-time Leaderboards** - Global and group-specific rankings
- **Speed Bonuses** - Extra points for quick answers

### ⚡ Performance & Reliability
- **24/7 Uptime** - Automatic crash recovery and restart
- **1000+ Group Support** - Handles massive concurrent usage
- **Rate Limiting** - Telegram API compliant with smart throttling
- **Error Handling** - Comprehensive logging and error reporting
- **Database Optimization** - MongoDB with proper indexing

### 🛠️ Technical Features
- **Async Architecture** - Built with python-telegram-bot v22.3
- **MongoDB Integration** - Scalable user data and game statistics
- **Heroku Ready** - Easy cloud deployment
- **VPS Compatible** - Systemd service included
- **Owner Commands** - Broadcast and administration tools

## 📋 Requirements

- Python 3.9+
- MongoDB (Atlas recommended)
- Telegram Bot Token
- 512MB+ RAM (for VPS deployment)

## 🔧 Installation

### Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/GuessWithEmojiBot.git
   cd GuessWithEmojiBot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start the bot**
   ```bash
   python main.py
   ```

### 🌐 Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-bot-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set BOT_TOKEN=your_bot_token
   heroku config:set MONGODB_URI=your_mongodb_uri
   heroku config:set OWNER_ID=your_telegram_id
   heroku config:set USE_WEBHOOK=true
   heroku config:set WEBHOOK_URL=https://your-bot-name.herokuapp.com
   ```

3. **Deploy**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push heroku main
   heroku ps:scale worker=1
   ```

### 🖥️ VPS Deployment

1. **Upload files to VPS**
   ```bash
   scp -r GuessWithEmojiBot/ user@your-vps-ip:/root/
   ```

2. **Run setup script**
   ```bash
   cd GuessWithEmojiBot
   chmod +x start.sh
   ./start.sh
   ```

3. **Start as systemd service**
   ```bash
   sudo systemctl start guesswithemojibot
   sudo systemctl status guesswithemojibot
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram bot token from BotFather | ✅ | - |
| `OWNER_ID` | Your Telegram user ID | ✅ | - |
| `MONGODB_URI` | MongoDB connection string | ✅ | - |
| `DATABASE_NAME` | MongoDB database name | ❌ | `emoji_movie_bot` |
| `GAME_TIMEOUT` | Game timeout in seconds | ❌ | `60` |
| `POINTS_CORRECT` | Points for correct answer | ❌ | `10` |
| `USE_WEBHOOK` | Enable webhook mode (Heroku) | ❌ | `false` |
| `WEBHOOK_URL` | Your app URL for webhooks | ❌ | - |
| `LOG_LEVEL` | Logging level | ❌ | `INFO` |

### MongoDB Setup

1. **Create MongoDB Atlas cluster** (free tier available)
2. **Create database user** with read/write permissions
3. **Whitelist IP addresses** (0.0.0.0/0 for development)
4. **Get connection string** and add to `.env`

Example MongoDB URI:
```
mongodb+srv://username:password@cluster0.mongodb.net/emoji_movie_bot?retryWrites=true&w=majority
```

## 🎮 Usage

### Bot Commands

#### 🎯 Game Commands
- `/start` - Initialize bot and show welcome message
- `/gen [category] [difficulty]` - Start new movie puzzle
- `/guess <movie name>` - Submit your guess
- `/hint` - Get a clue (limited per game)
- `/leaderboard` - View top players

#### 📊 Statistics Commands
- `/stats` - View your game statistics
- `/groupstats` - View group statistics (groups only)

#### ⚙️ Admin Commands (Owner Only)
- `/broadcast <message>` - Send message to all groups
- `/endgame` - Force end current game

### Game Examples

```
/gen hollywood easy
# 🎬 New Movie Puzzle!
# 🎯 Guess the movie: 🚢💔🧊
# 🇺🇸 Category: Hollywood
# 🟢 Difficulty: Easy

/guess Titanic
# 🎉 WINNER! 🎉
# 🏆 You got it right!
# 🎬 Answer: Titanic
# ⭐ Points Earned: 10
```

### Categories Available
- **Hollywood** 🇺🇸 - International blockbusters
- **Bollywood** 🇮🇳 - Hindi cinema classics  
- **Tollywood** 🎭 - Telugu cinema gems

### Difficulty Levels
- 🟢 **Easy** - Popular movies (1x points)
- 🟡 **Medium** - Moderate challenge (1.5x points)
- 🔴 **Hard** - True movie buffs (2x points)

## 📁 Project Structure

```
GuessWithEmojiBot/
├── bot/
│   ├── __init__.py
│   ├── bot.py              # Core bot logic
│   ├── commands.py         # Command handlers
│   ├── game_logic.py       # Game mechanics
│   └── broadcast.py        # Broadcast functionality
├── config/
│   ├── __init__.py
│   └── config.py           # Configuration management
├── database/
│   ├── __init__.py
│   ├── db.py              # MongoDB operations
│   └── models.py          # Data models
├── utils/
│   ├── __init__.py
│   ├── logger.py          # Logging system
│   ├── helpers.py         # Utility functions
│   └── movie_puzzles.py   # Puzzle management
├── game/
│   ├── __init__.py
│   ├── game.py           # Game session logic
│   └── leaderboard.py    # Scoring system
├── logs/                 # Log files
├── .env.example         # Environment template
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
├── Procfile           # Heroku deployment
├── start.sh          # VPS setup script
├── systemd.service   # Linux service file
└── README.md        # This file
```

## 🧩 Adding Custom Puzzles

### Method 1: Edit movie_puzzles.json

```json
{
  "hollywood": [
    {
      "emojis": "🕷️🕸️🌃",
      "answer": "Spider-Man",
      "difficulty": "easy",
      "hints": ["Marvel superhero", "Web slinger", "Peter Parker"]
    }
  ]
}
```

### Method 2: Direct Database Insert

```python
puzzle = MoviePuzzle(
    id="custom_1",
    emojis="🦁👑",
    answer="The Lion King",
    category="hollywood",
    difficulty=DifficultyLevel.EASY,
    hints=["Disney animated", "Simba", "Hakuna Matata"]
)
await db_manager.db.movie_puzzles.insert_one(puzzle.to_dict())
```

## 🚨 Error Handling & Monitoring

### Built-in Features
- **Automatic restart** on crashes
- **Error logging** to files and Telegram
- **Rate limit handling** with smart retries
- **Database connection recovery**
- **Memory usage monitoring**

### Monitoring Commands
```bash
# Check systemd service status
systemctl status guesswithemojibot

# View real-time logs
journalctl -u guesswithemojibot -f

# Check bot logs
tail -f logs/bot.log

# Monitor errors
tail -f logs/error.log
```

## 🔒 Security Features

- **Owner-only commands** with ID verification
- **Rate limiting** to prevent spam
- **Input sanitization** for all user inputs
- **Secure environment variables** handling
- **MongoDB injection prevention**

## 🚀 Performance Optimization

### Database Indexes
- User ID, username, score indexes for fast queries
- Game session indexes for active game lookup
- Puzzle category and difficulty indexes

### Rate Limiting
- 25 messages/second globally
- 20 messages/minute per group
- Smart retry with exponential backoff

### Memory Management
- Efficient data structures for active games
- Periodic cleanup of old game sessions
- Connection pooling for MongoDB

## 📈 Scaling Considerations

### For 1000+ Groups
- Use webhook mode on production
- Enable MongoDB connection pooling
- Implement horizontal scaling with load balancer
- Monitor memory usage and optimize as needed
- Consider Redis for caching frequently accessed data

### Resource Requirements

| Groups | RAM | CPU | MongoDB |
|--------|-----|-----|---------|
| 1-100 | 512MB | 1 core | Atlas M0 (Free) |
| 100-500 | 1GB | 1-2 cores | Atlas M2 |
| 500-1000 | 2GB | 2-4 cores | Atlas M5 |
| 1000+ | 4GB+ | 4+ cores | Atlas M10+ |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Troubleshooting

### Common Issues

**Bot not responding:**
- Check bot token is correct
- Verify MongoDB connection
- Check logs for errors

**Rate limit errors:**
- Reduce message frequency
- Check rate limiter configuration
- Monitor Telegram API limits

**Memory issues:**
- Increase server RAM
- Enable log rotation
- Clean up old data periodically

### Getting Help

1. **Check logs** first: `tail -f logs/bot.log`
2. **Search issues** on GitHub
3. **Create new issue** with logs and configuration
4. **Join our support group** on Telegram

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Custom puzzle categories
- [ ] Tournament mode
- [ ] Team-based gameplay
- [ ] Achievement system
- [ ] Integration with movie APIs
- [ ] Voice message hints
- [ ] Image puzzle support

## 📊 Statistics & Analytics

The bot tracks comprehensive statistics:
- User engagement metrics
- Popular puzzle categories
- Average solving times
- Group activity patterns
- Error rates and performance metrics

## 🌟 Acknowledgments

- **python-telegram-bot** team for the excellent library
- **MongoDB** for reliable database hosting
- **Telegram** for the powerful Bot API
- **Movie database** contributors for puzzle inspiration

---

**Built with ❤️ for the movie-loving Telegram community!**

*For enterprise deployments or custom features, please contact the development team.*
