import React from 'react';

const CURRENCY_SYMBOLS = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };

export function StatsBar({ stats, symbol }) {
    const {
        latestPrice,
        priceChange,
        avgSentiment,
        totalSignals,
        totalDataPoints,
        currency = 'USD',
    } = stats;

    const cs = CURRENCY_SYMBOLS[currency] || '$';
    const changeClass = priceChange > 0 ? 'positive' : priceChange < 0 ? 'negative' : 'neutral';
    const changeSign = priceChange > 0 ? '+' : '';
    const sentimentClass = avgSentiment > 0.1 ? 'positive' : avgSentiment < -0.1 ? 'negative' : 'neutral';

    return (
        <div className="stats-bar" style={{ marginBottom: 24 }}>
            <div className="glass-card stat-card">
                <span className="stat-label">{symbol} Price</span>
                <span className="stat-value">
                    {latestPrice !== null ? `${cs}${Number(latestPrice).toLocaleString()}` : '—'}
                </span>
                <span className={`stat-change ${changeClass}`}>
                    {latestPrice !== null ? `${changeSign}${priceChange.toFixed(3)}%` : 'Waiting...'}
                </span>
            </div>

            <div className="glass-card stat-card">
                <span className="stat-label">Avg Sentiment</span>
                <span className="stat-value">
                    {avgSentiment !== 0 ? avgSentiment.toFixed(2) : '—'}
                </span>
                <span className={`stat-change ${sentimentClass}`}>
                    {avgSentiment > 0.1 ? 'Bullish' : avgSentiment < -0.1 ? 'Bearish' : 'Neutral'}
                </span>
            </div>

            <div className="glass-card stat-card">
                <span className="stat-label">Signals</span>
                <span className="stat-value">{totalSignals}</span>
                <span className="stat-change neutral">SMA crossover</span>
            </div>

            <div className="glass-card stat-card">
                <span className="stat-label">Data Points</span>
                <span className="stat-value">{totalDataPoints}</span>
                <span className="stat-change neutral">Live ticks</span>
            </div>
        </div>
    );
}
