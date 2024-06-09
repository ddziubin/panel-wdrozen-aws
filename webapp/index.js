/* global gridjs, localStorage */
let BASE_REGION, BASE_CODECOMMIT_URL, BASE_CODEPIPELINE_URL, BASE_REPORT_URL, dashboardMeta;

const DATA_FILE_NAMES = [
  'data/dashboard-meta.json',
  'data/codecommit-data.json',
  'data/codebuild-cov-data.dev.json',
  'data/codebuild-unit-data.dev.json',
  'data/codepipeline-data.json',
];

const COLOR_MAP = {
  Succeeded: 'text-green-600',
  Failed: 'text-red-600',
  InProgress: 'text-blue-600',
  'N/A': 'text-red-600'
};
const notAvailable = gridjs.h('div', { className: 'font-bold' }, [
  gridjs.h(
    'span',
    { className: 'mx-1 text-slate-500 inline-block w-8' },
    'N/A'
  )
]);

function pipelineStatusLink(pipelineName, status) {
  return gridjs.h(
    'a',
    {
      href: `${BASE_CODEPIPELINE_URL}${pipelineName}/view`,
      target: '_blank',
      className: `mx-1 font-bold ${COLOR_MAP[status]}`
    },
    [status]
  );
}

function getPipelineTableRows(cell) {
  return Object.entries(cell).map(([key, value]) =>
    gridjs.h('tr', { class: 'border-b' }, [
      gridjs.h(
        'td',
        { class: 'text-xs px-0 py-0 font-bold text-slate-500 text-left w-50' },
        gridjs.h('br'),
        gridjs.h(
          'a',
          {
            className: `${COLOR_MAP[value]}`,
            href: `${BASE_CODEPIPELINE_URL}${key}/view`,
            target: '_blank'
          },
          value
        )
      )
    ])
  );
}
function getPipelineTable(projectName, tableRows) {
  return gridjs.h(
    'div',
    { className: `relative ${projectName}-pipeline-table-more hidden` },
    gridjs.h(
      'table',
      { className: 'border-collapse rounded-lg w-full' },
      tableRows
    ),
    gridjs.h(
      'svg',
      {
        xmlns: 'http://www.w3.org/2000/svg',
        fill: 'none',
        viewBox: '0 0 24 24',
        strokeWidth: 1.5,
        stroke: 'grey',
        className: 'w-4 h-4 absolute right-0 top-0 cursor-pointer',
        onclick: (e) => {
          e.preventDefault();
          document
            .querySelectorAll(`div.${projectName}-pipeline-table-less`)
            .forEach((el) => el.classList.toggle('hidden'));
          document
            .querySelectorAll(`div.${projectName}-pipeline-table-more`)
            .forEach((el) => el.classList.toggle('hidden'));
        }
      },
      gridjs.h('path', {
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        d: 'M18 12H6'
      })
    )
  );
}
function getPipelineSummaryColor(cell) {
  // All Pipelines for that project Succeeded
  if (Object.values(cell).every((attr) => attr === 'Succeeded')) {
    return COLOR_MAP.Succeeded;
  }
  // At least one Failed
  if (Object.values(cell).some((attr) => attr === 'Failed')) {
    return COLOR_MAP.Failed;
  }
  // None Failed but at least one is still in progress
  if (Object.values(cell).some((attr) => attr === 'InProgess')) {
    return COLOR_MAP.InProgress;
  } else {
    return 'text-slate-500';
  }
}
function getPipelineSummary(projectName, cell) {
  const numPipelines = Object.keys(cell).length;
  const pipeLineSummaryText = `${numPipelines} Pipeline${numPipelines === 1 ? '' : 's'
    }`;
  const summaryColor = getPipelineSummaryColor(cell);
  return gridjs.h(
    'div',
    { className: `relative ${projectName}-pipeline-table-less` },
    [
      gridjs.h(
        'span',
        { className: `mx-1 ${summaryColor} font-bold` },
        pipeLineSummaryText
      ),
      gridjs.h(
        'svg',
        {
          xmlns: 'http://www.w3.org/2000/svg',
          fill: 'currentColor',
          viewBox: '0 0 20 20',
          className: 'w-4 h-4 absolute right-0 top-0 cursor-pointer',
          onclick: (e) => {
            e.preventDefault();
            document
              .querySelectorAll(`div.${projectName}-pipeline-table-less`)
              .forEach((el) => el.classList.toggle('hidden'));
            document
              .querySelectorAll(`div.${projectName}-pipeline-table-more`)
              .forEach((el) => el.classList.toggle('hidden'));
          }
        },
        gridjs.h('path', {
          d: 'M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z'
        })
      )
    ]
  );
}
function sortStrings(line1, line2) {
  line1 = line1 || 'z';
  line2 = line2 || 'z';
  return line1 > line2 ? 1 : line1 < line2 ? -1 : 0;
}
function sortInts(line1, line2) {
  line1 = line1 ?? 0;
  line2 = line2 ?? 0;
  if (line1 > line2) {
    return 1;
  } else if (line2 > line1) {
    return -1;
  } else {
    return 0;
  }
}
function lastUpdated() {
  const currentTime = Math.floor(Date.now() / 1000);
  const elapsedTimeInSeconds = currentTime - dashboardMeta.lastUpdated;
  // Calculate elapsed days, hours, minutes, and seconds
  const days = Math.floor(elapsedTimeInSeconds / (60 * 60 * 24));
  const hours = Math.floor((elapsedTimeInSeconds % (60 * 60 * 24)) / (60 * 60));
  const minutes = Math.floor((elapsedTimeInSeconds % (60 * 60)) / 60);
  const seconds = elapsedTimeInSeconds % 60;
  let elapsedTimeString = 'Data Last Refreshed: ';
  if (days > 0) {
    elapsedTimeString += `${days} days `;
  }
  if (hours > 0) {
    elapsedTimeString += `${hours} hours `;
  }
  elapsedTimeString += `${minutes} minutes ${seconds} seconds ago`;
  return gridjs.h(
    'span',
    { className: 'inline-block text-gray-400 text-xs font-bold mx-3 my-3' },
    elapsedTimeString
  );
}
// Function to reload the page
function reloadPage() {
  window.location.reload();
}
let grid = null;
// const height = getWindowHeight();

function initDashboard() {
  Promise.all(
    DATA_FILE_NAMES.map((file) =>
      fetch(file)
        .then((response) => {
          if (!response.ok) {
            console.error('HTTP error ' + response.status);
            return [];
          }
          return response.json().catch((error) => {
            console.error('Parsing error for file: ' + file, error);
            return [];
          });
        })
        .catch(function () {
          console.error("This file can't be loaded: " + file);
          return [];
        })
    )
  )
    .then((loadedDataJSON) => {
      dashboardMeta = loadedDataJSON.shift();
      BASE_REGION = dashboardMeta.consoleDomain.split('.')[0];
      BASE_CODECOMMIT_URL = `https://${dashboardMeta.consoleDomain}/codesuite/codecommit/repositories/`;
      BASE_CODEPIPELINE_URL = `https://${dashboardMeta.consoleDomain}/codesuite/codepipeline/pipelines/`;

      const platformRepositories = loadedDataJSON.shift();
      const dashboardData = Object.assign(
        {},
        platformRepositories,
      );
      const covData = loadedDataJSON.shift();
      const unitData = loadedDataJSON.shift();

      // Merge CovData into Master Data
      Object.keys(dashboardData).forEach((projectKey) => {
        if (covData[projectKey]) {
          dashboardData[projectKey] = [
            ...dashboardData[projectKey],
            ...covData[projectKey]
          ];
        } else {
          dashboardData[projectKey] = [...dashboardData[projectKey], null, null];
        }
      });

      // Merge UnitData into Master Data
      Object.keys(dashboardData).forEach((projectKey) => {
        if (unitData[projectKey]) {
          dashboardData[projectKey] = [
            ...dashboardData[projectKey],
            ...unitData[projectKey]
          ];
        } else {
          dashboardData[projectKey] = [...dashboardData[projectKey], null];
        }
      });

      // Merge the Rest into Master Data
      loadedDataJSON.forEach((obj) => {
        // for each Object in the Master Data
        // For each Object in the current data file
        Object.keys(dashboardData).forEach((projectKey) => {
          if (obj[projectKey]) {
            dashboardData[projectKey] = [
              ...dashboardData[projectKey],
              ...obj[projectKey]
            ];
          } else {
            dashboardData[projectKey] = [...dashboardData[projectKey], null];
          }
        });
      });
      renderDashboard(Object.values(dashboardData));
    }
    );
}
function renderDashboard(dashboardData) {
  // console.log(dashboardData)
  grid = new gridjs.Grid({
    search: {
      keyword: localStorage.getItem('userFilter'),
      selector: (cell, rowIndex, cellIndex) => {
        if (cellIndex === 0) return cell;
        if (cellIndex in [1, 4]) return cell.join(' ');
        if (cellIndex === 5) return cell.map(obj => Object.values(obj).join(' ')).join(' ');
        return cell;
      }
    },
    fixedHeader: true,
    // height: `${height}px`,
    className: {
      table: 'text-xs'
    },
    sort: true,
    style: {
      td: {
        padding: '3px 6px'
      },
      th: {
        padding: '3px 6px'
      }
    },
    columns: [
      {
        id: 'project_name',
        name: 'Repository Name',
        width: '310px',
        formatter: (cell) =>
          gridjs.h(
            'div',
            {},
            gridjs.h('span', { className: 'inline-block' }, cell),

            gridjs.h(
              'a',
              {
                class: 'inline-block mx-2',
                href: `${BASE_CODECOMMIT_URL}${cell}/browse`,
                target: '_blank'
              },
              gridjs.h(
                'svg',
                {
                  xmlns: 'http://www.w3.org/2000/svg',
                  viewBox: '0 0 20 20',
                  stroke: 'blue',
                  className: 'w-4 h-4'
                },
                [
                  gridjs.h('path', {
                    fillRule: 'evenodd',
                    clipRule: 'evenodd',
                    d: 'M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z'
                  }),
                  gridjs.h('path', {
                    fillRule: 'evenodd',
                    clipRule: 'evenodd',
                    d: 'M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z'
                  })
                ]
              )
            )
          )
      },
      {
        id: 'tags',
        name: 'Repository Tags',
        width: '150px',
        formatter: (cell) => {
          return cell.map(item => gridjs.h('span', { className: 'font-bold' },
            gridjs.h('button', {
              className: 'mx-0.5 my-0.5 px-1 py-0 text-white bg-gray-400 border rounded-md pointer-events-none',
              cursor: 'none'
            }, item)
          )
          );
        }
      },
      {
        name: 'Outstanding Changes',
        columns: [
          {
            id: 'master_diff',
            name: 'Master -> Dev',
            type: 'integer',
            formatter: (cell, row) => {
              if (cell > 0) {
                return gridjs.h('div', { className: 'font-bold' }, [
                  gridjs.h(
                    'span',
                    { className: 'mx-2 text-red-600 inline-block' },
                    cell
                  ),
                  gridjs.h(
                    'button',
                    {
                      className:
                        'mx-1 px-1 py-0 text-white bg-blue-500 hover:bg-blue-600 border rounded-md',
                      onClick: () =>
                        window.open(
                          `${BASE_CODECOMMIT_URL}${row.cells[0].data}/pull-requests/new/refs/heads/int/.../refs/heads/dev?region=${BASE_REGION}`
                        )
                    },
                    'Open PR'
                  )
                ]);
              }
              if (cell === 0) {
                return gridjs.h(
                  'div',
                  { className: 'font-bold' },
                  gridjs.h(
                    'span',
                    { className: 'mx-2 text-green-600 inline-block w-8' },
                    cell
                  )
                );
              }
              return gridjs.h('div', { className: 'font-bold' }, [
                gridjs.h(
                  'span',
                  { className: 'mx-2 text-slate-500 inline-block w-8' },
                  'N/A'
                )
              ]);
            }
          },
          {
            id: 'prod_diff',
            name: 'Dev -> Prod',
            formatter: (cell, row) => {
              if (cell > 0) {
                return gridjs.h('div', { className: 'font-bold' }, [
                  gridjs.h(
                    'span',
                    { className: 'mx-2 text-red-600 inline-block w-8' },
                    cell
                  ),
                  gridjs.h(
                    'button',
                    {
                      className:
                        'mx-1 px-1 py-0 text-white bg-blue-500 hover:bg-blue-600 border rounded-md',
                      onClick: () =>
                        window.open(
                          `${BASE_CODECOMMIT_URL}${row.cells[0].data}/pull-requests/new/refs/heads/prod/.../refs/heads/int?region=${BASE_REGION}`
                        )
                    },
                    'Open PR'
                  )
                ]);
              }
              if (cell === 0) {
                return gridjs.h(
                  'div',
                  { className: 'font-bold' },
                  gridjs.h(
                    'span',
                    { className: 'mx-2 text-green-600 inline-block w-8' },
                    cell
                  )
                );
              }
              return gridjs.h('div', { className: 'font-bold' }, [
                gridjs.h(
                  'span',
                  { className: 'mx-2 text-slate-500 inline-block w-8' },
                  'N/A'
                )
              ]);
            }
          }
        ]
      },
      {
        id: 'branches',
        name: 'Branches',
        width: '300px',
        formatter: (cell, row) => {
          return cell.map((item) =>
            gridjs.h(
              'span',
              { className: 'inline-block' },
              gridjs.h(
                'a',
                {
                  className:
                    'text-blue-500 hover:text-blue-700 mx-1 break-words',
                  href: `${BASE_CODECOMMIT_URL}${row.cells[0].data}/browse/refs/heads/${item}`,
                  target: '_blank'
                },
                '\u2022 ',
                item
              )
            )
          );
        }
      },
      {
        id: 'pull_requests',
        name: 'Open Pull Requests',
        formatter: (cell, row) => {
          if (cell.length === 0) {
            return [];
          }
          const rowId = row.cells[0].data;
          const lessDetails = gridjs.h(
            'div',
            { className: `relative ${rowId}-less` },
            cell.map((item) => {
              return gridjs.h(
                'a',
                {
                  className: 'text-blue-500 hover:text-blue-700 mx-1',
                  href: `${BASE_CODECOMMIT_URL}${row.cells[0].data}/pull-requests/${item['Pull Request ID']}`,
                  target: '_blank'
                },
                item['Pull Request ID']
              );
            }),
            gridjs.h(
              'svg',
              {
                xmlns: 'http://www.w3.org/2000/svg',
                fill: 'none',
                viewBox: '0 0 24 24',
                strokeWidth: 1.5,
                stroke: 'grey',
                className: 'w-4 h-4 absolute right-0 top-0 cursor-pointer',
                onclick: (e) => {
                  e.preventDefault();
                  const less = document.querySelector(`div.${rowId}-less`);
                  const more = document.querySelector(`div.${rowId}-more`);
                  less.classList.toggle('hidden');
                  more.classList.toggle('hidden');
                }
              },
              gridjs.h('path', {
                strokeLinecap: 'round',
                strokeLinejoin: 'round',
                d: 'M12 6v12m6-6H6'
              })
            )
          );

          const moreDetails = gridjs.h(
            'div',
            { className: `relative ${rowId}-more  hidden` },
            cell.map((item) => {
              const prLink = gridjs.h(
                'a',
                {
                  className: 'text-blue-500 hover:text-blue-700',
                  href: `${BASE_CODECOMMIT_URL}${row.cells[0].data}/pull-requests/${item['Pull Request ID']}`,
                  target: '_blank'
                },
                item['Pull Request ID']
              );
              item['Pull Request ID'] = prLink;
              const tableRows = Object.entries(item).map(([key, value]) =>
                gridjs.h('tr', {}, [
                  gridjs.h(
                    'td',
                    {
                      class:
                        'bg-slate-50 rounded-l-lg border border-slate-300 font-semibold px-1 py-2 text-slate-500 text-left w-50'
                    },
                    key
                  ),
                  gridjs.h(
                    'td',
                    {
                      class:
                        'text-left border border-slate-300 py-2 px-1 text-slate-500'
                    },
                    value
                  )
                ])
              );
              return gridjs.h(
                'div',
                {
                  className:
                    'border border-slate-300 rounded-lg overflow-hidden my-2'
                },
                gridjs.h(
                  'table',
                  { className: 'border-collapse rounded-lg w-full' },
                  tableRows
                )
              );
            }),

            gridjs.h(
              'svg',
              {
                xmlns: 'http://www.w3.org/2000/svg',
                fill: 'none',
                viewBox: '0 0 24 24',
                strokeWidth: 1.5,
                stroke: 'grey',
                className: 'w-4 h-4 absolute right-0 top-0 cursor-pointer',
                onclick: (e) => {
                  e.preventDefault();
                  const less = document.querySelector(`div.${rowId}-less`);
                  const more = document.querySelector(`div.${rowId}-more`);
                  less.classList.toggle('hidden');
                  more.classList.toggle('hidden');
                }
              },
              gridjs.h('path', {
                strokeLinecap: 'round',
                strokeLinejoin: 'round',
                d: 'M18 12H6'
              })
            )
          );
          return [lessDetails, moreDetails];
        }
      },
      {
        name: 'Code Coverage',
        columns: [
          {
            id: 'linecoverage',
            name: 'Line',
            sort: {
              compare: sortInts
            },
            formatter: (cell) => {
              if (!cell) {
                return gridjs.h(
                  'b',
                  {
                    className: 'mx-1 text-slate-500'
                  },
                  'N/A'
                );
              } else {
                const colorLines =
                  cell >= 75 ? 'text-green-600' : 'text-red-600';
                return [
                  gridjs.h(
                    'b',
                    {
                      className: `mx-1 ${colorLines}`
                    },
                    `${cell}% `
                  )
                ];
              }
            }
          },
          {
            id: 'branchcoverage',
            name: 'Branch',
            sort: {
              compare: sortInts
            },
            formatter: (cell) => {
              if (!cell) {
                return gridjs.h(
                  'b',
                  {
                    className: 'mx-1 text-slate-500'
                  },
                  'N/A'
                );
              } else {
                const colorBranches =
                  cell >= 75 ? 'text-green-600' : 'text-red-600';
                return [
                  gridjs.h(
                    'b',
                    {
                      className: `mx-1 ${colorBranches}`
                    },
                    `${cell}% `
                  )
                ];
              }
            }
          }
        ]
      },
      {
        id: 'unit_tests',
        name: 'Unit Tests',
        sort: {
          compare: sortInts
        },
        formatter: (cell) => {
          if (!cell) {
            return notAvailable;
          } else {
            return gridjs.h(
              'span',
              {
                className: 'mx-1 font-bold'
              },
              [
                gridjs.h(
                  'b',
                  { className: 'text-green-600', title: 'Passed' },
                  cell[0]
                ),
                gridjs.h('b', { className: 'text-slate-500' }, ' / '),
                gridjs.h(
                  'b',
                  { className: 'text-yellow-600', title: 'Skipped' },
                  cell[1]
                ),
                gridjs.h('b', { className: 'text-slate-500' }, ' / '),
                gridjs.h(
                  'b',
                  { className: 'text-red-600', title: 'Failed' },
                  cell[2]
                ),
                gridjs.h('b', { className: 'text-slate-500' }, ' / '),
                gridjs.h(
                  'b',
                  { className: 'text-slate-600', title: 'Total' },
                  cell[3]
                )
              ]
            );
          }
        }
      },
      {
        name: 'Pipeline Status',
        columns: [
          {
            id: 'dev_build',
            name: 'Dev Org',
            sort: {
              compare: sortStrings
            },
            formatter: (cell, row) => {
              if (!cell) {
                return notAvailable;
              }
              const projectName = row.cells[0].data;
              const pipelineName = `${projectName}-pipeline`;
              if (cell && typeof cell === 'object') {
                const tableRows = getPipelineTableRows(cell);
                const pipelineTable = getPipelineTable(projectName, tableRows);
                const pipelineSummary = getPipelineSummary(projectName, cell);
                return [pipelineTable, pipelineSummary];
              } else {
                return pipelineStatusLink(pipelineName, cell);
              }
            }
          }
        ]
      }
    ],
    data: dashboardData
  });
  grid.plugin.add({
    id: 'lastUpdatedplugin',
    component: lastUpdated,
    position: gridjs.PluginPosition.Header,
    order: 2
  });
  const wrapperElement = document.getElementById('wrapper');
  // Wipe the Element HTML just in case we are reinitalizing.
  wrapperElement.innerHTML = '';
  grid.render(wrapperElement);
  document.querySelector('.gridjs-search input').addEventListener('input', function (event) {
    localStorage.setItem('userFilter', event.target.value);
  });
}

initDashboard();
// Reload the page when the tab becomes visible
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState === 'visible') {
    reloadPage();
  }
});

// Reload the Page every 5 minutes
// setInterval(reloadPage, 300000);
