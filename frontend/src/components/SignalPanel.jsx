import React from 'react';

export function SignalPanel({ data }) {
    const signals = data
        .filter(msg => msg.type === 'signal')
        .slice(-10)
        .reverse();

    return (
        <div className="glass-card signal-container">
            <div className="signal-header">
                <span className="signal-title">Trade Signals</span>
                <span className="feed-count">{signals.length}</span>
            </div>

            {signals.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">⚡</div>
                    <span>No signals yet — SMA engine needs data...</span>
                </div>
            ) : (
                <ul className="signal-list">
                    {signals.map((sig, index) => {
                        const isBuy = sig.signal_type === 'BUY';
                        const direction = isBuy ? 'buy' : 'sell';
                        const time = sig.timestamp
                            ? new Date(sig.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                            })
                            : '';

                        return (
                            <li key={index} className={`signal-card ${direction}`}>
                                <span className={`signal-badge ${direction}`}>
                                    {sig.signal_type}
                                </span>
                                <div className="signal-info">
                                    <div className="signal-symbol">
                                        {sig.symbol}
                                        {sig.price && (
                                            <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8, fontSize: '0.8rem' }}>
                                                ${Number(sig.price).toLocaleString()}
                                            </span>
                                        )}
                                    </div>
                                    <div className="signal-details">{sig.details}</div>
                                </div>
                                <span className="signal-time">{time}</span>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}
