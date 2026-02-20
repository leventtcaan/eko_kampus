import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import apiClient from '../api/client';

interface Task {
  id: number;
  title: string;
  desc: string;
  target: number;
  current: number;
  reward: number;
  icon: string;
}

export default function BountyScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get('reports/tasks/')
      .then((res) => setTasks(res.data))
      .catch((err) => console.error('Görevler yüklenemedi:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Yükleniyor...</Text>
      </View>
    );
  }

  const renderTask = ({ item }: { item: Task }) => {
    const done = item.current >= item.target;
    const progress = Math.min(item.current / item.target, 1);

    return (
      <View style={[styles.card, done && styles.cardDone]}>
        {/* Üst satır: ikon + başlık/açıklama + ödül rozeti */}
        <View style={styles.cardTop}>
          <Text style={styles.cardIcon}>{item.icon}</Text>

          <View style={styles.cardText}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.cardDesc}>{item.desc}</Text>
          </View>

          <View style={styles.rewardBadge}>
            <Text style={styles.rewardText}>🟡 {item.reward}</Text>
            <Text style={styles.rewardSub}>puan</Text>
          </View>
        </View>

        {/* İlerleme çubuğu */}
        <View style={styles.progressBg}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>

        {/* Alt satır: sayaç + tamamlandı rozeti */}
        <View style={styles.cardBottom}>
          <Text style={styles.progressLabel}>
            {Math.min(item.current, item.target)}/{item.target} Tamamlandı
          </Text>
          {done && (
            <View style={styles.doneBadge}>
              <Text style={styles.doneBadgeText}>✓ Tamamlandı</Text>
            </View>
          )}
        </View>
      </View>
    );
  };

  return (
    <FlatList
      data={tasks}
      keyExtractor={(item) => String(item.id)}
      contentContainerStyle={styles.list}
      ListHeaderComponent={
        <Text style={styles.header}>Günlük Görevler</Text>
      }
      renderItem={renderTask}
      ListEmptyComponent={
        <Text style={styles.empty}>Henüz görev yok.</Text>
      }
    />
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#888',
    fontSize: 14,
  },
  list: {
    padding: 20,
    gap: 14,
  },
  header: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 8,
  },
  empty: {
    textAlign: 'center',
    color: '#bbb',
    marginTop: 40,
    fontSize: 14,
  },

  // Görev kartı
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 3,
  },
  cardDone: {
    backgroundColor: '#f0faf0',
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 14,
  },
  cardIcon: {
    fontSize: 34,
  },
  cardText: {
    flex: 1,
    gap: 3,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1a1a1a',
  },
  cardDesc: {
    fontSize: 12,
    color: '#777',
  },
  rewardBadge: {
    backgroundColor: '#FFF8E1',
    borderRadius: 10,
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FFD740',
  },
  rewardText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#F9A825',
  },
  rewardSub: {
    fontSize: 10,
    color: '#F9A825',
    fontWeight: '500',
  },

  // İlerleme çubuğu
  progressBg: {
    height: 8,
    backgroundColor: '#e8e8e8',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 4,
  },

  // Alt satır
  cardBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  progressLabel: {
    fontSize: 12,
    color: '#888',
    fontWeight: '500',
  },
  doneBadge: {
    backgroundColor: '#4CAF50',
    borderRadius: 8,
    paddingVertical: 3,
    paddingHorizontal: 10,
  },
  doneBadgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
});
