// 'use server';

import { initializeApp, cert, getApps } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { getFirestore } from "firebase-admin/firestore";

const firebaseConfig = {
//   type: process.env.FIREBASE_TYPE,
  projectId: process.env.FIREBASE_PROJECT_ID,
  clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
  privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
//   client_id: process.env.FIREBASE_CLIENT_ID,
//   auth_uri: process.env.FIREBASE_AUTH_URI,
//   token_uri: process.env.FIREBASE_TOKEN_URI,
//   auth_provider_x509_cert_url: process.env.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
//   client_x509_cert_url: process.env.FIREBASE_CLIENT_X509_CERT_URL,
//   universe_domain: process.env.FIREBASE_UNIVERSE_DOMAIN,
};

const initFirebaseAdmin = () => {
    const apps = getApps();

    if (!apps.length) {
        initializeApp({
            credential: cert(firebaseConfig),
            databaseURL: process.env.FIREBASE_DATABASE_URL,
        });
    }
    return {
        auth : getAuth(),
        db: getFirestore()
    }
};

export const {auth, db} = initFirebaseAdmin();

