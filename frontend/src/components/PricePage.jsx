import React from 'react';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { MarketChart } from './MarketChart';
import { SentimentFeed } from './SentimentFeed';
import { SignalPanel } from './SignalPanel';
import { StatsBar } from './StatsBar';

export function PricePage({
    isConnected,
    tickers,
    selectedCategory,
    handleCategoryChange,
    selectedSymbol,
    setSelectedSymbol,
    stats,
    messages,
    currentCurrency,
    currentAssets,
    categoryOrder
}) {
    return (
        <div className="app-container price-page">
            {/* Header */}
            <div className="app-header header">
                <div className="header-left">
                    <div className="app-logo">
                        <div className={`logo-dot ${isConnected ? 'connected' : 'disconnected'}`} />
                        <h1>TradeSentient</h1>
                    </div>
                </div>

                <div className="header-right">
                    <div className="animation-top-right">
                        <video
                            src="/animations/header.webm"
                            autoPlay
                            loop
                            muted
                            playsInline
                            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                        />
                    </div>
                    <div className={`status-badge ${isConnected ? 'connected' : 'disconnected'}`}>
                        <span>{isConnected ? '● Live' : '○ Offline'}</span>
                    </div>
                </div>
            </div>

            {/* Category Tabs */}
            <div className="category-tabs">
                {categoryOrder.map(cat => {
                    const label = tickers?.[cat]?.label || cat;
                    return (
                        <button
                            key={cat}
                            className={`category-tab ${selectedCategory === cat ? 'active' : ''}`}
                            onClick={() => handleCategoryChange(cat)}
                        >
                            <span className="category-icon">
                                {cat === 'crypto' ? '₿' : cat === 'us_stock' ? '🇺🇸' : '🇮🇳'}
                            </span>
                            {label}
                        </button>
                    );
                })}
            </div>

            {/* Symbol Tabs */}
            <div className="symbol-tabs">
                {currentAssets.map(asset => (
                    <button
                        key={asset.symbol}
                        className={`symbol-tab ${selectedSymbol === asset.symbol ? 'active' : ''}`}
                        onClick={() => setSelectedSymbol(asset.symbol)}
                        title={asset.name}
                    >
                        {asset.symbol}
                    </button>
                ))}
            </div>

            {/* Stats Bar */}
            <StatsBar stats={stats} symbol={selectedSymbol} />

            {/* Dashboard Grid */}
            <div className="dashboard-grid">
                <div className="main-col">
                    <MarketChart data={messages} symbol={selectedSymbol} currency={currentCurrency} />
                </div>
                <div className="side-col">
                    <SentimentFeed data={messages} />
                    <SignalPanel data={messages} />
                </div>
            </div>
        </div>
    );
}
