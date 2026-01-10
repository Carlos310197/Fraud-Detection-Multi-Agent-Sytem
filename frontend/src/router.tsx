import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import Transactions from './pages/Transactions';
import TransactionDetail from './pages/TransactionDetail';
import HitlQueue from './pages/HitlQueue';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Transactions />,
      },
      {
        path: 'transactions/:id',
        element: <TransactionDetail />,
      },
      {
        path: 'hitl',
        element: <HitlQueue />,
      },
    ],
  },
]);

export default router;
