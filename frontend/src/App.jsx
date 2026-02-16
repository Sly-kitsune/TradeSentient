import React, { useState, useEffect, useMemo } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { MarketChart } from './components/MarketChart';
import { SentimentFeed } from './components/SentimentFeed';
import { SignalPanel } from './components/SignalPanel';
import { LoadingPage } from './components/LoadingPage';
import { PricePage } from './components/PricePage';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

const CATEGORY_ORDER = ['crypto', 'us_stock', 'in_stock'];

function App() {
    const { messages, isConnected, subscribe } = useWebSocket(`${WS_BASE}/ws`);

    const [tickers, setTickers] = useState(null);
    const [selectedCategory, setSelectedCategory] = useState('crypto');
    const [selectedSymbol, setSelectedSymbol] = useState('BTC');

    // Fetch tickers from backend on mount
    useEffect(() => {
        fetch(`${API_BASE}/tickers`)
            .then(res => res.json())
            .then(data => {
                setTickers(data);
            })
            .catch(err => {
                console.error('Failed to fetch tickers:', err);
                // Fallback if backend is not ready
                setTickers({
                    crypto: {
                        label: 'Crypto', assets: [
                            { symbol: 'BTC', name: 'Bitcoin' }, { symbol: 'ETH', name: 'Ethereum' },
                            { symbol: 'SOL', name: 'Solana' }, { symbol: 'ADA', name: 'Cardano' },
                            { symbol: 'XRP', name: 'Ripple' }, { symbol: 'DOGE', name: 'Dogecoin' },
                            { symbol: 'MATIC', name: 'Polygon' },
                        ]
                    },
                    us_stock: {
                        label: 'US Stocks', assets: [
                            { symbol: 'AAPL', name: 'Apple' }, { symbol: 'GOOGL', name: 'Alphabet' },
                            { symbol: 'TSLA', name: 'Tesla' }, { symbol: 'MSFT', name: 'Microsoft' },
                            { symbol: 'AMZN', name: 'Amazon' }, { symbol: 'NFLX', name: 'Netflix' },
                        ]
                    },
                    in_stock: {
                        label: 'Indian Stocks', assets: [
                            { symbol: 'RELIANCE', name: 'Reliance' }, { symbol: 'TCS', name: 'TCS' },
                            { symbol: 'INFY', name: 'Infosys' }, { symbol: 'HDFCBANK', name: 'HDFC Bank' },
                        ]
                    },
                });
            });
    }, []);

    // Subscribe WebSocket to selected symbol
    useEffect(() => {
        if (isConnected && selectedSymbol) {
            subscribe(selectedSymbol);
        }
    }, [isConnected, selectedSymbol, subscribe]);

    // Get current category assets
    const currentAssets = useMemo(() => {
        if (!tickers || !tickers[selectedCategory]) return [];
        return tickers[selectedCategory].assets || [];
    }, [tickers, selectedCategory]);

    // Get currency for current category
    const currentCurrency = useMemo(() => {
        if (!tickers || !tickers[selectedCategory]) return 'USD';
        return tickers[selectedCategory].currency || 'USD';
    }, [tickers, selectedCategory]);

    // Derive stats from messages
    const stats = useMemo(() => {
        const marketMsgs = messages.filter(
            m => m.type === 'market' && m.symbol === selectedSymbol
        );
        const sentimentMsgs = messages.filter(m => m.type === 'sentiment');
        const signalMsgs = messages.filter(m => m.type === 'signal');

        const latestPrice = marketMsgs.length > 0
            ? marketMsgs[marketMsgs.length - 1].price
            : null;

        const prevPrice = marketMsgs.length > 1
            ? marketMsgs[marketMsgs.length - 2].price
            : null;

        const priceChange = latestPrice && prevPrice
            ? ((latestPrice - prevPrice) / prevPrice * 100)
            : 0;

        const avgSentiment = sentimentMsgs.length > 0
            ? sentimentMsgs.reduce((sum, m) => sum + m.score, 0) / sentimentMsgs.length
            : 0;

        return {
            latestPrice,
            priceChange,
            avgSentiment,
            totalSignals: signalMsgs.length,
            totalDataPoints: marketMsgs.length,
            currency: currentCurrency,
        };
    }, [messages, selectedSymbol, currentCurrency]);

    // Handle category switch
    const handleCategoryChange = (cat) => {
        setSelectedCategory(cat);
        // Auto-select first symbol in new category
        if (tickers && tickers[cat]?.assets?.length > 0) {
            setSelectedSymbol(tickers[cat].assets[0].symbol);
        }
    };

    if (!tickers) {
        return <LoadingPage />;
    }

    return (
        <PricePage
            isConnected={isConnected}
            tickers={tickers}
            selectedCategory={selectedCategory}
            handleCategoryChange={handleCategoryChange}
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol}
            stats={stats}
            messages={messages}
            currentCurrency={currentCurrency}
            currentAssets={currentAssets}
            categoryOrder={CATEGORY_ORDER}
        />
    );
}

export default App;