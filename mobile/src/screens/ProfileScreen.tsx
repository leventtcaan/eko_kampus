import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

interface Profile {
  first_name: string;
  last_name: string;
  email: string;
  waste_count: number;
  issue_count: number;
}

export default function ProfileScreen() {
  const { logout, userToken } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get('auth/me/', { headers: { Authorization: `Bearer ${userToken}` } })
      .then((res) => setProfile(res.data))
      .catch((err) => console.error('Profil yüklenemedi:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => {
    Alert.alert('Çıkış Yap', 'Hesabından çıkış yapmak istediğine emin misin?', [
      { text: 'Vazgeç', style: 'cancel' },
      { text: 'Çıkış Yap', style: 'destructive', onPress: logout },
    ]);
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>👤</Text>
        </View>

        {loading ? (
          <ActivityIndicator color="#4CAF50" style={{ marginBottom: 8 }} />
        ) : (
          <>
            <Text style={styles.name}>
              {profile ? `${profile.first_name} ${profile.last_name}` : 'Yükleniyor...'}
            </Text>
            <Text style={styles.email}>{profile?.email ?? ''}</Text>
          </>
        )}

        {/* Başarı kutuları */}
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statIcon}>♻️</Text>
            <Text style={styles.statValue}>{profile?.waste_count ?? '—'}</Text>
            <Text style={styles.statLabel}>Atık</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={styles.statIcon}>🕵️</Text>
            <Text style={styles.statValue}>{profile?.issue_count ?? '—'}</Text>
            <Text style={styles.statLabel}>Dedektif</Text>
          </View>
        </View>
      </View>

      <View style={styles.spacer} />

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Çıkış Yap</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f8f7',
    padding: 24,
    paddingTop: 60,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 28,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 4,
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#e8f5e9',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  avatarText: {
    fontSize: 40,
  },
  name: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 4,
  },
  email: {
    fontSize: 13,
    color: '#888',
    fontWeight: '500',
    marginBottom: 20,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f7f8f7',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 24,
    gap: 0,
  },
  statBox: {
    flex: 1,
    alignItems: 'center',
    gap: 3,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: '#ddd',
  },
  statIcon: {
    fontSize: 22,
  },
  statValue: {
    fontSize: 20,
    fontWeight: '800',
    color: '#4CAF50',
  },
  statLabel: {
    fontSize: 11,
    color: '#999',
    fontWeight: '600',
  },
  spacer: {
    flex: 1,
  },
  logoutBtn: {
    backgroundColor: '#E53935',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
    shadowColor: '#E53935',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  logoutText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '700',
  },
});
