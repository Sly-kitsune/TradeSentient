import React from 'react';

export function SentimentFeed({ data }) {
    const filteredData = data
        .filter(msg => msg.type === 'sentiment')
        .slice(-15)
        .reverse();

    return (
        <div className="glass-card feed-container">
            <div className="feed-header">
                <span className="feed-title">Sentiment Feed</span>
                <span className="feed-count">{filteredData.length}</span>
            </div>

            {filteredData.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">💬</div>
                    <span>Waiting for sentiment data...</span>
                </div>
            ) : (
                <ul className="feed-list">
                    {filteredData.map((msg, index) => {
                        const source = (msg.source || 'unknown').toLowerCase();
                        const score = msg.score ?? 0;
                        const isPositive = score > 0;
                        const barWidth = Math.abs(score) * 100;

                        return (
                            <li key={index} className="feed-item">
                                <span className={`feed-source ${source}`}>
                                    {source}
                                </span>
                                <div className="feed-text">{msg.text}</div>
                                <div className="feed-score-bar">
                                    <div
                                        className={`fill ${isPositive ? 'positive' : 'negative'}`}
                                        style={{ width: `${barWidth}%` }}
                                    />
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}
