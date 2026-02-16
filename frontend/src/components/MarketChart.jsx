import React from 'react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer
} from 'recharts';

const CURRENCY_SYMBOLS = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };

function CustomTooltip({ active, payload, label, currency }) {
    if (!active || !payload || !payload.length) return null;
    const cs = CURRENCY_SYMBOLS[currency] || '$';
    return (
        <div className="custom-tooltip">
            <div className="label">{label}</div>
            <div className="value">{cs}{payload[0].value?.toLocaleString()}</div>
        </div>
    );
}

export function MarketChart({ data, symbol, currency = 'USD' }) {
    const cs = CURRENCY_SYMBOLS[currency] || '$';

    const filteredData = data
        .filter(msg => msg.type === 'market' && msg.symbol === symbol)
        .map(msg => ({
            ...msg,
            timestamp: new Date(msg.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }),
            price: Number(msg.price),
        }))
        .slice(-50);

    return (
        <div className="glass-card chart-container">
            <div className="chart-header">
                <div>
                    <div className="chart-title">{symbol} Price Feed</div>
                    <div className="chart-subtitle">Last {filteredData.length} data points · Live · {currency}</div>
                </div>
            </div>

            {filteredData.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">📈</div>
                    <span>Waiting for {symbol} data...</span>
                </div>
            ) : (
                <div style={{ height: '320px', width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={filteredData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                            <defs>
                                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                                    <stop offset="50%" stopColor="#8b5cf6" stopOpacity={0.1} />
                                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="rgba(255,255,255,0.04)"
                                vertical={false}
                            />
                            <XAxis
                                dataKey="timestamp"
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                                tickLine={false}
                                interval="preserveStartEnd"
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                axisLine={false}
                                tickLine={false}
                                tickFormatter={val => `${cs}${val.toLocaleString()}`}
                                width={80}
                            />
                            <Tooltip content={<CustomTooltip currency={currency} />} />
                            <Area
                                type="monotone"
                                dataKey="price"
                                stroke="#6366f1"
                                strokeWidth={2}
                                fill="url(#priceGradient)"
                                isAnimationActive={true}
                                animationDuration={600}
                                animationEasing="ease-out"
                                dot={false}
                                activeDot={{
                                    r: 5,
                                    fill: '#6366f1',
                                    stroke: '#fff',
                                    strokeWidth: 2,
                                }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}
