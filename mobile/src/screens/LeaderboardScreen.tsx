import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

interface LeaderboardEntry {
  id: number;
  name: string;
  points: number;
  rank: number;
}

const MEDAL: Record<number, string> = { 1: '👑', 2: '🥈', 3: '🥉' };

const AVATAR_COLORS = [
  '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
  '#F44336', '#00BCD4', '#FF5722', '#607D8B',
];

function avatarColor(id: number) {
  return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

function initials(name: string) {
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default function LeaderboardScreen() {
  const { userToken } = useAuth();
  const [data, setData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLeaderboard = useCallback(() => {
    setLoading(true);
    apiClient
      .get('auth/leaderboard/', { headers: { Authorization: `Bearer ${userToken}` } })
      .then((res) => setData(res.data))
      .catch((err) => console.error('Liderlik tablosu yüklenemedi:', err))
      .finally(() => setLoading(false));
  }, [userToken]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  const renderItem = ({ item }: { item: LeaderboardEntry }) => {
    const medal = MEDAL[item.rank];
    const isTop3 = item.rank <= 3;

    return (
      <View style={[styles.row, isTop3 && styles.rowTop3]}>
        <View style={styles.rankContainer}>
          {medal ? (
            <Text style={styles.medal}>{medal}</Text>
          ) : (
            <Text style={styles.rankText}>{item.rank}</Text>
          )}
        </View>

        <View style={[styles.avatar, { backgroundColor: avatarColor(item.id) }]}>
          <Text style={styles.avatarText}>{initials(item.name)}</Text>
        </View>

        <Text style={styles.name} numberOfLines={1}>{item.name}</Text>

        <View style={styles.pointsBadge}>
          <Text style={styles.pointsValue}>{item.points}</Text>
          <Text style={styles.pointsLabel}>puan</Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>🏆 Liderlik Tablosu</Text>

      {loading ? (
        <ActivityIndicator color="#4CAF50" style={{ marginTop: 40 }} />
      ) : data.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>🌱</Text>
          <Text style={styles.emptyText}>Henüz puan kazanan kullanıcı yok.</Text>
          <Text style={styles.emptySubText}>İlk sen ol!</Text>
        </View>
      ) : (
        <FlatList
          data={data}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f8f7',
    paddingTop: 60,
  },
  header: {
    fontSize: 22,
    fontWeight: '800',
    color: '#1a1a1a',
    textAlign: 'center',
    marginBottom: 20,
    paddingHorizontal: 24,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    gap: 10,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
    gap: 12,
  },
  rowTop3: {
    borderWidth: 1.5,
    borderColor: '#FFD700',
  },
  rankContainer: {
    width: 32,
    alignItems: 'center',
  },
  medal: {
    fontSize: 22,
  },
  rankText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#888',
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  name: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#1a1a1a',
  },
  pointsBadge: {
    alignItems: 'center',
    backgroundColor: '#e8f5e9',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 60,
  },
  pointsValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#4CAF50',
  },
  pointsLabel: {
    fontSize: 10,
    color: '#81C784',
    fontWeight: '600',
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 80,
  },
  emptyIcon: {
    fontSize: 52,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#555',
    marginBottom: 4,
  },
  emptySubText: {
    fontSize: 13,
    color: '#999',
  },
});
