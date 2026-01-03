import React from 'react';
import { Card } from '../ui/Card';
import type { GrantData } from '../../types';
import { DollarSign, Calendar, Building2, Award } from 'lucide-react';

interface GrantDataDisplayProps {
  data: GrantData;
}

export const GrantDataDisplay: React.FC<GrantDataDisplayProps> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* Basic Information */}
      <Card title="Grant Information">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start">
            <Building2 className="h-5 w-5 text-primary-600 mt-1 mr-3" />
            <div>
              <p className="text-sm text-gray-600">Organization</p>
              <p className="font-medium">{data.organization_name || 'N/A'}</p>
            </div>
          </div>

          <div className="flex items-start">
            <Award className="h-5 w-5 text-primary-600 mt-1 mr-3" />
            <div>
              <p className="text-sm text-gray-600">Funder</p>
              <p className="font-medium">{data.funder_name || 'N/A'}</p>
            </div>
          </div>

          <div className="flex items-start">
            <DollarSign className="h-5 w-5 text-primary-600 mt-1 mr-3" />
            <div>
              <p className="text-sm text-gray-600">Grant Amount</p>
              <p className="font-medium">
                {data.grant_amount
                  ? `$${data.grant_amount.toLocaleString()}`
                  : 'N/A'}
              </p>
            </div>
          </div>

          <div className="flex items-start">
            <Calendar className="h-5 w-5 text-primary-600 mt-1 mr-3" />
            <div>
              <p className="text-sm text-gray-600">Grant Period</p>
              <p className="font-medium">{data.grant_period || 'N/A'}</p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t">
          <p className="text-sm text-gray-600 mb-2">Grant Title</p>
          <p className="font-medium text-lg">{data.grant_title || 'N/A'}</p>
        </div>
      </Card>

      {/* Timeline */}
      {data.timeline && data.timeline.items.length > 0 && (
        <Card title="Timeline & Milestones">
          <div className="space-y-3">
            {data.timeline.items.map((item, index) => (
              <div
                key={index}
                className="flex items-start p-3 bg-gray-50 rounded-md"
              >
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-primary-600">
                      {item.date}
                    </span>
                    {item.amount && (
                      <span className="text-sm font-medium text-green-600">
                        {item.amount}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700">{item.description}</p>
                  {item.category && (
                    <span className="inline-block mt-1 px-2 py-1 text-xs bg-primary-100 text-primary-700 rounded">
                      {item.category}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Budget */}
      {data.budget && data.budget.items.length > 0 && (
        <Card title="Budget Breakdown">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.budget.items.map((item, index) => (
                  <tr key={index}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {item.category}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {item.description || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                      ${item.amount.toLocaleString()}
                    </td>
                  </tr>
                ))}
                <tr className="bg-gray-50">
                  <td
                    colSpan={2}
                    className="px-4 py-3 text-sm font-bold text-gray-900"
                  >
                    Total
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-bold text-gray-900">
                    ${data.budget.total_grant_amount.toLocaleString()}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Work Plan */}
      {data.workplan && data.workplan.tasks.length > 0 && (
        <Card title="Work Plan">
          <div className="mb-4 pb-4 border-b">
            <p className="text-sm text-gray-600">Project Title</p>
            <p className="font-medium text-lg">{data.workplan.project_title}</p>
          </div>

          <div className="space-y-4">
            {data.workplan.tasks.map((task, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-md">
                <h4 className="font-medium text-gray-900 mb-2">
                  {index + 1}. {task.task_name}
                </h4>
                <p className="text-sm text-gray-700 mb-2">{task.description}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  {task.start_date && (
                    <div>
                      <span className="text-gray-600">Start: </span>
                      <span className="font-medium">{task.start_date}</span>
                    </div>
                  )}
                  {task.end_date && (
                    <div>
                      <span className="text-gray-600">End: </span>
                      <span className="font-medium">{task.end_date}</span>
                    </div>
                  )}
                  {task.responsible_party && (
                    <div>
                      <span className="text-gray-600">Responsible: </span>
                      <span className="font-medium">{task.responsible_party}</span>
                    </div>
                  )}
                  {task.deliverables && (
                    <div className="md:col-span-2">
                      <span className="text-gray-600">Deliverables: </span>
                      <span className="font-medium">{task.deliverables}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};